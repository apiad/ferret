---
number: 1
title: "🚀 Roadmap to v1.0: Stability, Scalability, and Live Observability"
---

**Description:**

This tracking issue consolidates the architectural improvements required to move Ferret from v0.1.0 to a production-ready v1.0. The primary goals are to remove fragile instrumentation logic, ensure non-blocking writes to BeaverDB, and transform Ferret into a real-time observability platform.

### Core Architecture & Stability

* **Issue #2:** [Stability] Refactor Instrumentation to Remove "Magical" Builtins Injection
* **Issue #3:** [Performance] Implement Non-Blocking Write Buffer with Background Worker
* **Issue #6:** [Cost Control] Implement Adaptive Rate Limiting (Throughput-Based Sampling)

### Analysis & Visualization

* **Issue #4:** [Scalability] Implement Streaming Analysis to Prevent OOM on Large Datasets
* **Issue #5:** [Usability] Implement Flame Graph Export (Speedscope Support)

### Live Observability (The "Watch" Command)

* **Issue #8:** [Observability] Implement Live Monitoring System (`ferret watch`)
* **Issue #9:** [Reliability] Deadlock & Stall Detection (The Watchdog)
* **Issue #10:** [Observability] Capture Thread and Process Context in Spans

### Developer Experience

* **Issue #7:** [Usability] Enable Profiling of Installed Modules via CLI (`-m` flag)
