from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import uuid
import time


class SpanModel(BaseModel):
    """
    Represents a single unit of work (trace) in the system.
    """

    span_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    parent_id: Optional[str] = None
    name: str

    # Timing
    start_time: float = Field(default_factory=time.time)
    end_time: Optional[float] = None
    duration: Optional[float] = None

    # Metadata
    tags: Dict[str, Any] = Field(default_factory=dict)
    status: str = "ok"  # "ok", "error"

    def finish(self, status: str = "ok"):
        """Completes the span calculation."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.status = status


@dataclass
class AggregatedStats:
    """
    Summary statistics for a specific function/span name across a run.
    """

    name: str
    count: int
    total_duration: float
    avg_duration: float
    min_duration: float
    max_duration: float
    error_count: int
    error_rate: float


@dataclass
class TraceNode:
    """
    A node in the execution tree representing a single span and its children.
    """

    span: SpanModel
    children: list["TraceNode"] = field(default_factory=list)

    @property
    def total_children_duration(self) -> float:
        return sum(child.span.duration or 0.0 for child in self.children)

    @property
    def self_time(self) -> float:
        """Time spent in this span excluding child spans."""
        duration = self.span.duration or 0.0
        return max(0.0, duration - self.total_children_duration)
