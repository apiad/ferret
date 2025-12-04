from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from collections import defaultdict
import statistics

from beaver import BeaverDB
from .models import SpanModel, AggregatedStats, TraceNode


class Report:
    def __init__(self, db_path: Union[str, BeaverDB], namespace: str = "_ferret_trace"):
        """
        Initialize the Report engine.

        Args:
            db_path: Path to the .db file OR an existing BeaverDB instance.
            namespace: The name of the log to read from.
        """
        if isinstance(db_path, BeaverDB):
            self.db = db_path
            self._owns_db = False
        else:
            self.db = BeaverDB(db_path)
            self._owns_db = True

        # Initialize the log manager with the SpanModel to ensure auto-deserialization
        self.log_manager = self.db.log(namespace, model=SpanModel)

    def _fetch_spans(self, run_id: str) -> List[SpanModel]:
        """Helper to fetch and filter spans for a specific run."""
        # In a production scenario with massive logs, we would want
        # time-range filtering or a secondary index.
        # For a profiler, scanning the log for a run_id is acceptable.
        all_entries = list(self.log_manager)
        return [entry[1] for entry in all_entries if entry[1].run_id == run_id]

    def analyze_run(self, run_id: str) -> Dict[str, AggregatedStats]:
        """
        Computes aggregated statistics grouped by span name.
        Useful for identifying "hot spots" (functions taking the most time).
        """
        spans = self._fetch_spans(run_id)

        stats = {}
        grouped = defaultdict(list)
        for span in spans:
            grouped[span.name].append(span)

        for name, group in grouped.items():
            # Filter out unfinished spans (shouldn't happen in valid traces)
            durations = [s.duration for s in group if s.duration is not None]
            errors = [s for s in group if s.status != "ok"]

            if not durations:
                continue

            count = len(group)
            stats[name] = AggregatedStats(
                name=name,
                count=count,
                total_duration=sum(durations),
                avg_duration=statistics.mean(durations),
                min_duration=min(durations),
                max_duration=max(durations),
                error_count=len(errors),
                error_rate=len(errors) / count if count > 0 else 0.0,
            )

        return stats

    def build_trees(self, run_id: str) -> List[TraceNode]:
        """
        Reconstructs the hierarchical call stacks for a given run.
        Returns a list of root nodes (spans with no parents in this context).
        """
        spans = self._fetch_spans(run_id)

        # Create all nodes first
        span_map = {s.span_id: TraceNode(span=s) for s in spans}
        roots = []

        # Link children to parents
        for span in spans:
            node = span_map[span.span_id]
            if span.parent_id and span.parent_id in span_map:
                parent = span_map[span.parent_id]
                parent.children.append(node)
            else:
                # If no parent_id, or parent is missing from this run data, treat as root
                roots.append(node)

        # Sort roots by start time
        roots.sort(key=lambda x: x.span.start_time)
        return roots

    def close(self):
        if self._owns_db:
            self.db.close()
