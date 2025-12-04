from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import uuid
import time

class SpanModel(BaseModel):
    """
    Represents a single unit of work (trace) in the system.
    """
    span_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    parent_id: Optional[str] = None
    name: str

    # Timing
    start_time: float = Field(default_factory=time.time)
    end_time: Optional[float] = None
    duration: Optional[float] = None

    # Metadata
    tags: Dict[str, Any] = Field(default_factory=dict)
    status: str = "ok"  # "ok", "error"

    def finish(self, status: str = "ok"):
        """Completes the span calculation."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.status = status
