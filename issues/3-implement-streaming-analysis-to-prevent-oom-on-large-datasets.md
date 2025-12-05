---
number: 3
title: "Implement Streaming Analysis to Prevent OOM on Large Datasets"
state: open
labels:
---

**Description:**

The current implementation of `ferret/report.py` loads the entire dataset for a given `run_id` into memory before processing it. specifically, the `_fetch_spans` method executes `list(self.log_manager)`, which materializes every single log entry into a Python list.

For short scripts, this is fine. However, for long-running processes (e.g., a web server running for days) that generate millions of spans, this will inevitably cause an **Out-of-Memory (OOM)** crash, making it impossible to analyze the data.

**Proposed Solution:**

Refactor the reporting engine to use a **Streaming Pipeline**. Instead of fetching all data at once, the system should iterate over the database records one by one (using generators), update the aggregated statistics incrementally, and discard the raw records immediately.

**Tasks:**

* [ ] **Generator Interface (`ferret/report.py`):**
    * Refactor `_fetch_spans` to return a `Generator[SpanModel]` instead of a `List[SpanModel]`.
    * Ensure that the underlying `BeaverDB` iteration is lazy (checking `self.log_manager` behavior to ensure it doesn't pre-load).
* [ ] **Streaming Aggregation:**
    * Rewrite `analyze_run` to remove the `grouped = defaultdict(list)` logic, which also buffers data in memory.
    * Implement a `StreamingStats` class that accepts a single span at a time and updates `count`, `total_duration`, `min`, and `max` in-place.
* [ ] **Tree Building Optimization (Partial):**
    * *Note: Full tree building requires all nodes, which is hard to stream.*
    * Implement a "Top N Roots" filter that only keeps the N slowest root nodes in memory while discarding faster ones during the iteration, allowing for partial tree analysis of massive datasets without blowing up memory.

**Acceptance Criteria:**

* The `analyze` command can process a database file larger than the available RAM (e.g., a 2GB trace file on a 1GB RAM container) without crashing.
* Memory usage remains relatively flat during analysis, proportional to the number of *unique function names*, not the total number of logs.