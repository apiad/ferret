---
number: 9
title: "Deadlock & Stall Detection (The Watchdog)"
state: open
labels:
---

**Description:**

In a complex async or multi-threaded application, tasks often get "stuck" due to deadlocks (waiting on a lock that never releases), infinite loops, or hanging network requests. Since Ferret will track "Open Spans" (active functions) in real-time (via Issue 7), we can implement a **Watchdog** that identifies spans that have been running longer than a safety threshold.

**Proposed Solution:**

1.  **Stall Detection:** The `ferret watch` system scans the list of active spans. If a span's duration exceeds a configured `stall_threshold` (e.g., 10s), it is flagged as "Stalled".
2.  **Stack Trace Dumping:** When a stall is detected, Ferret should attempt to capture the exact line number where the code is stuck.
    * *For Threads:* Use `sys._current_frames()` to find the stack trace of the thread owning the span.
    * *For Async:* Inspect the `asyncio` task associated with the span.

**Tasks:**

* [ ] **Configuration (`ferret/core.py`):**
    * Add `stall_threshold` (float, seconds) to `Profiler` config.
    * Add `enable_watchdog` (bool).
* [ ] **Watchdog Thread (`ferret/watchdog.py`):**
    * Create a daemon thread that wakes up periodically (e.g., every 5s).
    * Iterate over all active `Span` objects in memory.
    * If `(time.now() - span.start_time) > stall_threshold`:
        * Mark span status as `STALLED`.
        * **Capture Context:** Grab the current stack trace for that thread/task using `traceback` and `sys._current_frames()`.
        * Emit a `METRIC` or `ERROR` event to BeaverDB containing this stack dump.
* [ ] **UI Integration (`ferret/tui.py`):**
    * Update `ferret watch` to show a "💀 Deadlocks / Stalls" section.
    * Highlight stalled spans in **Red** in the Live Tree.
    * Allow the user to click a stalled span to see the captured stack trace (telling them exactly *where* the deadlock is).

**Acceptance Criteria:**

* If a profiled function sleeps for 30s (with a 5s threshold), it appears in the "Deadlocks" list after 5s.
* The detailed view shows the filename and line number (e.g., `await future` or `lock.acquire()`) where the code is hanging.