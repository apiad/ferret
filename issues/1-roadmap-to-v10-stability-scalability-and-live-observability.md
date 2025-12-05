---
number: 1
title: "🚀 Roadmap to v1.0: Stability, Scalability, and Live Observability"
state: open
labels:
---

**Description:**

This tracking issue consolidates the architectural improvements required to move Ferret from v0.1.0 to a production-ready v1.0. The primary goals are to remove fragile instrumentation logic, ensure non-blocking writes to BeaverDB, and transform Ferret into a real-time observability platform.

### Core Architecture & Stability

* **Issue #2:** Replace fragile `builtins` injection with a robust singleton accessor pattern.
* **Issue #3:** Move BeaverDB writes to a background thread to prevent blocking the application loop.
* **Issue #6:** Implement throughput-based adaptive rate limiting to control overhead.

### Analysis & Visualization

* **Issue #4:** Refactor reporting to use streaming iterators to handle large datasets without OOM.
* **Issue #5:** Export traces to Speedscope JSON format for flame graph visualization.

### Live Observability

* **Issue #8:** Create `ferret watch` TUI for real-time monitoring of active spans and metrics.
* **Issue #9:** Add watchdog to detect and report stalled spans or deadlocks.
* **Issue #10:** Capture PID and Thread ID in spans to visualize concurrency.

### Developer Experience

* **Issue #7:** Support `ferret run -m <module>` to profile installed CLI tools easily.