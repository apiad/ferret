---
number: 1
title: "🚀 Roadmap to v1.0: Stability, Scalability, and Sampling"
state: open
labels:
---

**Description:**
This tracking issue consolidates the architectural improvements required to move Ferret from v0.1.0 to a production-ready v1.0. The primary goals are to remove fragile instrumentation logic, ensure non-blocking writes to BeaverDB, and support large-scale analysis via streaming.


### 1. Stability: Remove "Magical" Builtins Injection

**Priority:** Critical

**Context:** The current CLI relies on injecting `_ferret_profiler` into `builtins`. This is fragile and causes conflicts if user code shadows this variable.

- [ ] **Refactor Core**: Implement a singleton accessor pattern in `ferret.core` (e.g., `get_global_profiler()`).
- [ ] **Update Instrumentor**: Modify `FerretInstrumentor` in `ferret/cli.py` to inject safe import statements (`from ferret.core import ...`) instead of relying on globals.
- [ ] **Expand Coverage**: Update the AST visitor to support `ast.Lambda` and investigate support for module-level code.

### 2. Performance: Non-Blocking Write Buffer

**Priority:** High

**Context:** `Profiler._record_span` currently uses a `threading.Lock` and processes logic in the application thread. This introduces latency in high-concurrency `asyncio` applications.

- [ ] **Implement Queue**: Replace the list buffer with `queue.SimpleQueue` for thread-safe, lock-free appending.
- [ ] **Background Worker**: Offload the BeaverDB flush operation to a daemon `threading.Thread` that consumes the queue.
- [ ] **Graceful Shutdown**: Update `Profiler.close()` to signal the worker thread and ensure the queue is fully drained before exit.

### 3. Scalability: Streaming Analysis

**Priority:** High

**Context:** `Report._fetch_spans` loads all traces for a run into memory. This causes OOM errors on large datasets.

- [ ] **Generator Interface**: Refactor `report.py` to iterate over BeaverDB entries using a generator rather than fetching lists.
- [ ] **Streaming Aggregation**: Rewrite `analyze_run` to compute `AggregatedStats` incrementally during iteration.

### 4. Usability: Flame Graph Export

**Priority:** Medium

**Context:** The current tree visualization is difficult to parse for deep call stacks. Standard profiling tools use Flame Graphs.

- [ ] **New Command**: Add `ferret export --format speedscope` to the CLI.
- [ ] **Transformer**: Implement a conversion from `TraceNode` structures to the JSON format required by [speedscope.app](https://www.speedscope.app/).

### 5. Cost Control: Adaptive Rate Limiting

**Priority:** Medium

**Context:** Fixed probabilistic sampling is difficult to tune manually. A burst of activity might still overwhelm the storage, while quiet periods might be under-sampled.

- [ ] **Config**: Add `max_spans_per_second` (default: 1000) to `Profiler` init.
- [ ] **Token Bucket Algorithm**: Implement a lightweight token bucket or sliding window counter in `Profiler`.
- [ ] **Automatic Throttling**: If the rate limit is exceeded, `start`/`measure` should automatically return a `NoOpSpan` until the rate stabilizes, ensuring the logging overhead never exceeds a set budget regardless of traffic.
