---
number: 6
title: "Implement Non-Blocking Write Buffer with Background Worker"
state: open
labels:
---

**Description:**

Currently, the `Profiler._record_span` method executes in the main application thread. It uses a `threading.Lock` to protect the buffer and, when the buffer is full, performs a synchronous flush to `BeaverDB` (file I/O) within the same thread.

In high-concurrency `asyncio` applications or CPU-intensive workloads, this design introduces two major performance bottlenecks:

1.  **Thread Contention:** The lock forces serialization of all span completions. If 1,000 tasks finish simultaneously, they must wait in line to record their data.
2.  **I/O Latency:** Flushing to disk (even if buffered) blocks the application's execution flow, causing unpredictable latency spikes in endpoint responses.

**Proposed Solution:**

Decouple the "recording" of a span from the "persistence" of that span. Use a lock-free, thread-safe queue to accept spans immediately, and move all file I/O operations to a dedicated daemon thread.

**Tasks:**

* [ ] **Queue Implementation (`ferret/core.py`):**
    * Replace the `self._buffer` list and `self._buffer_lock` with a `queue.SimpleQueue` (unbounded) or `queue.Queue` (bounded, to prevent OOM).
    * Update `_record_span` to simply `put()` the span model into the queue. This operation is atomic and requires no explicit locking.
* [ ] **Background Worker:**
    * Add a `_background_writer` method that runs in a loop, consuming items from the queue.
    * Implement batching logic inside the worker: wait for `buffer_size` items or a timeout (e.g., 0.5s) before writing to `BeaverDB`.
    * Start this worker as a `daemon` thread in `Profiler.__init__`.
* [ ] **Graceful Shutdown:**
    * Update `Profiler.close()` to send a "poison pill" or set a `threading.Event` to stop the worker.
    * Ensure `close()` waits (`thread.join()`) for the worker to finish flushing the remaining queue items before returning.

**Acceptance Criteria:**

* `_record_span` returns immediately without acquiring locks or performing I/O.
* Heavy loads (e.g., 10,000 spans/sec) do not block the main execution thread.
* All queued spans are successfully flushed to disk upon `profiler.close()`.