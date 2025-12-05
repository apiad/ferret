---
number: 10
title: "Capture Thread and Process Context in Spans"
state: open
labels:
---

**Description:**

To visualize "where" code is executing in the proposed TUI (`ferret watch`), we need to know which thread and process owns each span. Currently, `SpanModel` only captures timing and hierarchy data. Without this, the live monitor cannot group active spans by thread (e.g., "Thread-1 is executing `fetch_db`", "MainProcess is executing `setup`") or distinguish between multiple worker processes running in parallel.

**Proposed Solution:**

1.  **Schema Update:** Add `thread_id`, `thread_name`, and `process_id` fields to the `SpanModel`.
2.  **Capture Logic:** During `Span` initialization in the Profiler, automatically capture these values using Python's standard `os` and `threading` libraries.

**Tasks:**

  * [ ] **Update Model (`ferret/models.py`):**
      * Add fields to `SpanModel`:
          * `process_id: int`
          * `thread_id: int`
          * `thread_name: str` (Optional, but highly recommended for TUI readability)
  * [ ] **Update Core (`ferret/core.py`):**
      * In `Span.__init__`, capture the context:
        ```python
        import os
        import threading

        # ... inside __init__
        self.model.process_id = os.getpid()
        self.model.thread_id = threading.get_ident()
        self.model.thread_name = threading.current_thread().name
        ```
  * [ ] **TUI Integration Prep:**
      * Ensure these fields are indexed or easily accessible so the future `ferret watch` app can group the "Live Stack" by `process_id -> thread_id`.

**Acceptance Criteria:**

  * Inspecting the `ferret.db` (via `ferret analyze` or raw check) shows that every span now contains valid PID and Thread ID information.
  * Spans generated from `asyncio` tasks correctly reflect the thread running the event loop (usually MainThread).
  * Spans generated from `concurrent.futures.ThreadPoolExecutor` show distinct `thread_id`s.