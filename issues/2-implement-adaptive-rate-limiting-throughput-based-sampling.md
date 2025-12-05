---
number: 2
title: "Implement Adaptive Rate Limiting (Throughput-Based Sampling)"
state: open
labels:
---

**Description:**

Currently, Ferret profiles every single execution that it instruments. In a production environment with variable traffic, this is dangerous. A sudden burst of activity (e.g., a DDoS attack or a viral event) could cause the profiler to generate thousands of spans per second, overwhelming `BeaverDB` and degrading the performance of the main application.

Static probabilistic sampling (e.g., "sample 10%") is often insufficient because 10% of a massive spike is still too much, while 10% of a quiet period provides too little data.

**Proposed Solution:**

Implement **Adaptive Rate Limiting** using a Token Bucket or Sliding Window algorithm. Instead of a fixed probability, the user configures a `max_spans_per_second` budget. The profiler automatically accepts or rejects traces to stay within this budget, ensuring a predictable overhead ceiling regardless of incoming traffic volume.

**Tasks:**

* [ ] **Configuration (`ferret/core.py`):**
    * Add a `max_spans_per_second` argument to `Profiler.__init__` (default: `1000`).
    * Initialize a "Token Bucket" state (current tokens, last refill time).
* [ ] **Throttling Logic:**
    * Modify `Profiler.start()` and `Profiler.measure()`.
    * Before creating a real `Span`, check if a token is available.
    * **If Yes:** Decrement token count, create and return a real `Span` (or `SpanContext`).
    * **If No:** Return a `NoOpSpan` (a dummy object that conforms to the Span interface but does no recording and holds no data).
* [ ] **NoOpSpan Implementation:**
    * Create a lightweight class `NoOpSpan` that implements `__enter__`, `__exit__`, `annotate`, and `end` as empty methods to ensure user code (e.g., `span.annotate(...)`) doesn't crash when throttled.

**Acceptance Criteria:**

* Setting `max_spans_per_second=10` limits the output to ~10 traces per second even if the loop runs 100 times per second.
* When traffic drops below the limit, profiling resumes immediately (tokens refill).
* Application code using `with profiler.measure(...) as span:` runs without errors even when the span is dropped.