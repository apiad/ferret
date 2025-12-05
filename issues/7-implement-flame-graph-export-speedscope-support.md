---
number: 7
title: "Implement Flame Graph Export (Speedscope Support)"
state: open
labels:
---

**Description:**

The current hierarchical tree visualization in the CLI (`ferret analyze --tree`) is useful for quick checks, but it becomes unreadable for deep call stacks or complex async traces. Text-based trees cannot effectively visualize time-line distribution or "icicle" views, which are standard for performance engineering.

To make Ferret a viable tool for deep performance debugging, we need to export data in a format compatible with standard visualization tools.

**Proposed Solution:**

Implement a new `export` command that generates a JSON file compatible with **[Speedscope](https://www.speedscope.app/)**, a popular web-based flame graph viewer. Speedscope supports an "Evented Profile" format (using Open/Close frame events) which maps perfectly to our Start/End span model.

**Tasks:**

  * [ ] **CLI Command (`ferret/cli.py`):**
      * Add a new command `ferret export`.
      * Arguments:
          * `db_path`: Path to the database.
          * `--run-id`: Specific run to export (default to latest).
          * `--format`: Output format (default to `speedscope`).
          * `--output` / `-o`: Destination file path (e.g., `ferret_trace.json`).
  * [ ] **Transformer Logic (`ferret/export.py`):**
      * Create a new module `ferret.export`.
      * Implement a transformer that reads `SpanModel` objects from `BeaverDB` and converts them into the [Speedscope File Format Schema](https://github.com/jlfwong/speedscope/wiki/Importing-from-custom-formats).
      * *Tip:* Use the "Evented Profile" format. Iterate through spans and emit an `OPEN_FRAME` event at `start_time` and a `CLOSE_FRAME` event at `end_time` (calculated via `start_time + duration`).
  * [ ] **Refinement:**
      * Ensure the time units match Speedscope requirements (microseconds or seconds).
      * Map `span.name` to the frame name.
      * Map `span.tags` to frame args (if supported) or append interesting tags to the frame name for visibility.

**Acceptance Criteria:**

  * Running `ferret export --output trace.json` generates a valid JSON file.
  * Uploading `trace.json` to [speedscope.app](https://www.speedscope.app) successfully renders a generic Flame Graph and a Time Order view.
  * The visualization accurately reflects the nesting and duration of the recorded spans.