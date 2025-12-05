---
number: 8
title: "Implement Live Monitoring System (`ferret watch`)"
state: open
labels:
---

**Description:**

Currently, Ferret is a "post-mortem" analysis tool. It records span data to `BeaverDB`, and users must run `ferret analyze` *after* the fact to see what happened. This model is insufficient for debugging real-time performance issues, such as stuck processes, deadlocks, or live memory leaks.

To support real-time observability, we need a system that can visualize the *current* state of the application, including active (unfinished) spans and system-level metrics (CPU, RAM, Threads).

**Proposed Solution:**

1.  **Event Sourcing Model:** Transition the storage model from logging just "Finished Spans" to logging "Lifecycle Events" (`SPAN_START` and `SPAN_END`). This allows a watcher to reconstruct the "currently open" call stack.
2.  **System Telemetry:** Introduce a background thread in the Profiler that logs system metrics (CPU, Memory, Active Tasks) at a fixed interval.
3.  **TUI Dashboard:** Create a new CLI command `ferret watch` using **Textual** that connects to the `BeaverDB` in read-only mode, tails the log stream, and visualizes the live state.

**Tasks:**

* [ ] **Data Model Updates (`ferret/models.py`):**
    * Define a generic `LogEntry` model that can represent different event types: `SPAN_START`, `SPAN_END`, and `METRIC`.
    * Update `SpanModel` to support being serialized as partial events.
* [ ] **Profiler Logic (`ferret/core.py`):**
    * Update `Profiler.start()` (and `__enter__`) to immediately write a `SPAN_START` event to the non-blocking queue.
    * Update `Span.end()` to write a `SPAN_END` event.
    * Implement `SystemSampler`: A daemon thread that wakes up every 1s, captures `psutil` stats and `threading.active_count()`, and writes a `METRIC` event.
* [ ] **The Watcher App (`ferret/tui.py`):**
    * Create a **Textual** application.
    * **Live Tailer:** Implement a utility that reads `BeaverDB` from the last known offset, yielding new records as they appear.
    * **State Reconstruction:** Maintain an in-memory tree of "Open Spans" based on the Start/End events received.
    * **UI Layout:**
        * **Live Stack:** A Tree widget showing currently running functions and their elapsed time.
        * **Metrics:** Sparklines or numeric indicators for CPU/RAM.
        * **Recent Activity:** A scrolling table of the most recently finished spans.

**Acceptance Criteria:**

* `ferret watch` launches a TUI dashboard.
* When the profiled script sleeps or performs a long task, the function appears in the "Live Stack" view immediately.
* When the function finishes, it disappears from the "Live Stack" and appears in the "Recent Activity" table.
* System metrics (CPU/RAM) update in real-time (approx. every second).