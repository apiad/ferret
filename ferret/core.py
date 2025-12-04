import asyncio
import time
import functools
import inspect
import threading
import atexit
import uuid
from contextvars import ContextVar
from typing import Callable, Any, Optional, List, Union, cast

from beaver import BeaverDB
from .models import SpanModel

# --- Context Management ---

# Tracks the current active Span ID for the current task/thread.
# Default is None (Root context).
_current_span_ctx: ContextVar[Optional[str]] = ContextVar("current_span", default=None)


class Profiler:
    def __init__(
        self,
        db_path: str | BeaverDB = ":memory:",
        buffer_size: int = 100,
        namespace: str = "_ferret_trace",
        run_id: str = None
    ):
        """
        Initialize the Profiler.

        Args:
            db_path: Path to .db file OR an existing BeaverDB instance.
            buffer_size: Number of spans to hold in memory before flushing.
            namespace: The name of the log in BeaverDB.
            run_id: A unique ID for this execution session. Defaults to a UUID.
        """
        if isinstance(db_path, BeaverDB):
            self.db = cast(BeaverDB, db_path)
            self._owns_db = False
        else:
            self.db = BeaverDB(db_path)
            self._owns_db = True

        self.log_manager = self.db.log(namespace, model=SpanModel)
        self.run_id = run_id or uuid.uuid4().hex

        # Buffering
        self._buffer: List[SpanModel] = []
        self._buffer_lock = threading.Lock()
        self._buffer_size = buffer_size

        # Ensure we flush on exit
        atexit.register(self.flush)

    def measure(self, name: str | Callable[..., str], tags: dict = None) -> "SpanContext":
        """
        The main entry point. Returns a context manager that can also be used as a decorator.
        """
        return SpanContext(self, name, tags)

    def start(self, name: str, tags: dict = None) -> "Span":
        """
        Manual start method. Returns a Span object that MUST be ended manually.
        Useful for callback-based async code where context managers don't fit.
        """
        # Get parent from implicit context
        parent_id = _current_span_ctx.get()

        span = Span(
            profiler=self,
            name=name,
            parent_id=parent_id,
            initial_tags=tags,
            run_id=self.run_id
        )

        # We do NOT set the contextvar here because manual start/stop
        # usually implies disconnected execution flows.
        return span

    def _record_span(self, span_model: SpanModel):
        """
        Internal method to add a finished span to the buffer.
        """
        with self._buffer_lock:
            self._buffer.append(span_model)
            should_flush = len(self._buffer) >= self._buffer_size

        if should_flush:
            self.flush()

    def flush(self):
        """
        Writes pending spans to BeaverDB in a batch.
        """
        with self._buffer_lock:
            if not self._buffer:
                return

            # Swap buffer ref to unblock other threads quickly
            pending = self._buffer
            self._buffer = []

        # Write to DB (BeaverDB handles the transaction/locking)
        try:
            with self.log_manager.batched() as batch:
                for span in pending:
                    # We use the span's start_time as the log timestamp
                    batch.log(span, timestamp=span.start_time)
        except Exception as e:
            # Fallback: print error, maybe retry?
            # For a profiler, dropping data is better than crashing app.
            print(f"[Ferret] Failed to flush traces: {e}")

    def close(self):
        self.flush()
        if self._owns_db:
            self.db.close()


class Span:
    """
    The actual object holding trace data.
    """
    def __init__(self, profiler: Profiler, name: str, parent_id: str | None, initial_tags: dict | None, run_id: str):
        self.profiler = profiler
        self.model = SpanModel(
            name=name,
            parent_id=parent_id,
            tags=initial_tags or {},
            run_id=run_id
        )

    def annotate(self, **kwargs):
        """Add metadata tags to the span mid-flight."""
        self.model.tags.update(kwargs)

    def end(self, status="ok"):
        """Stops the timer and sends the span to the profiler."""
        self.model.finish(status)
        self.profiler._record_span(self.model)


class SpanContext:
    """
    A dual-purpose class acting as:
    1. Sync Context Manager
    2. Async Context Manager
    3. Decorator (Sync & Async)
    """
    def __init__(
        self,
        profiler: Profiler,
        name: str | Callable[..., str],
        tags: dict = None
    ):
        self.profiler = profiler
        self._name_or_func = name
        self.tags = tags
        self.token = None
        self.span: Span | None = None

    def _get_name(self, args=None, kwargs=None) -> str:
        """Resolves dynamic naming if a callable was passed."""
        if callable(self._name_or_func):
            try:
                return self._name_or_func(args or (), kwargs or {})
            except Exception:
                return "unknown_dynamic_span"
        return self._name_or_func

    # --- Context Manager Protocol (Sync) ---

    def __enter__(self):
        name = self._get_name()
        parent_id = _current_span_ctx.get()

        self.span = Span(self.profiler, name, parent_id, self.tags, self.profiler.run_id)

        # Set Context
        self.token = _current_span_ctx.set(self.span.model.span_id)

        return self.span

    def __exit__(self, exc_type, exc_value, traceback):
        status = "error" if exc_type else "ok"

        # Restore Context
        if self.token:
            _current_span_ctx.reset(self.token)

        if self.span:
            if exc_value:
                self.span.annotate(error=str(exc_value), error_type=exc_type.__name__)
            self.span.end(status)

    # --- Context Manager Protocol (Async) ---

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_value, traceback):
        self.__exit__(exc_type, exc_value, traceback)

    # --- Decorator Protocol ---

    def __call__(self, func):
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Resolve dynamic name using runtime args
                if callable(self._name_or_func):
                    self._resolved_name = self._name_or_func(args)
                else:
                    self._resolved_name = self._name_or_func

                # Manually trigger the context logic with the resolved name
                # We create a new, temporary context to ensure thread safety
                # (reusing 'self' across concurrent calls is bad)
                ctx = SpanContext(self.profiler, self._resolved_name, self.tags)
                async with ctx:
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                if callable(self._name_or_func):
                    self._resolved_name = self._name_or_func(args)
                else:
                    self._resolved_name = self._name_or_func

                ctx = SpanContext(self.profiler, self._resolved_name, self.tags)
                with ctx:
                    return func(*args, **kwargs)
            return sync_wrapper