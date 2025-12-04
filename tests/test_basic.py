import pytest
import asyncio
import time
import os
from ferret.core import Profiler
from ferret.report import Report

# --- Fixtures ---


@pytest.fixture
def db_path(tmp_path):
    """Returns a temporary path for a SQLite database."""
    return str(tmp_path / "test_ferret.db")


@pytest.fixture
def profiler(db_path):
    """Returns a Profiler instance with a known run_id."""
    return Profiler(db_path, run_id="test_run_1", buffer_size=1)


# --- Sync Tests ---


def test_basic_measurement(profiler):
    with profiler.measure("root_task"):
        time.sleep(0.01)

    # buffer_size=1, so it should be flushed immediately
    report = Report(profiler.db)
    stats = report.analyze_run("test_run_1")

    assert "root_task" in stats
    assert stats["root_task"].count == 1
    assert stats["root_task"].avg_duration >= 0.01


def test_decorator_usage(profiler):
    @profiler.measure("decorated_func")
    def my_func():
        return "result"

    assert my_func() == "result"

    report = Report(profiler.db)
    stats = report.analyze_run("test_run_1")
    assert "decorated_func" in stats
    assert stats["decorated_func"].count == 1


def test_dynamic_naming(profiler):
    @profiler.measure(lambda args: f"user_{args[0]}")
    def process_user(uid):
        pass

    process_user(42)

    report = Report(profiler.db)
    stats = report.analyze_run("test_run_1")
    assert "user_42" in stats


def test_hierarchy_contextvars(profiler):
    with profiler.measure("parent") as parent:
        with profiler.measure("child"):
            pass

    report = Report(profiler.db)
    roots = report.build_trees("test_run_1")

    assert len(roots) == 1
    root = roots[0]
    assert root.span.name == "parent"
    assert len(root.children) == 1
    assert root.children[0].span.name == "child"
    assert root.children[0].span.parent_id == root.span.span_id


def test_explicit_start_stop(profiler):
    span = profiler.start("manual_task")
    time.sleep(0.01)
    span.end()

    report = Report(profiler.db)
    stats = report.analyze_run("test_run_1")
    assert "manual_task" in stats


def test_annotations(profiler):
    with profiler.measure("search") as span:
        span.annotate(hits=10)

    # We need to dig into the raw spans to check tags
    # Since Report primarily does stats/trees, let's look at the tree
    report = Report(profiler.db)
    roots = report.build_trees("test_run_1")

    assert roots[0].span.tags["hits"] == 10


# --- Async Tests ---


@pytest.mark.asyncio
async def test_async_measurement(profiler):
    async with profiler.measure("async_task"):
        await asyncio.sleep(0.01)

    report = Report(profiler.db)
    stats = report.analyze_run("test_run_1")
    assert "async_task" in stats


@pytest.mark.asyncio
async def test_async_decorator(profiler):
    @profiler.measure("async_func")
    async def work():
        await asyncio.sleep(0.01)
        return True

    result = await work()
    assert result is True

    report = Report(profiler.db)
    stats = report.analyze_run("test_run_1")
    assert "async_func" in stats


@pytest.mark.asyncio
async def test_async_hierarchy(profiler):

    @profiler.measure("leaf")
    async def leaf():
        pass

    @profiler.measure("middle")
    async def middle():
        await leaf()

    async with profiler.measure("root"):
        await middle()

    report = Report(profiler.db)
    roots = report.build_trees("test_run_1")

    # Tree: root -> middle -> leaf
    assert len(roots) == 1
    node_root = roots[0]
    assert node_root.span.name == "root"

    assert len(node_root.children) == 1
    node_middle = node_root.children[0]
    assert node_middle.span.name == "middle"

    assert len(node_middle.children) == 1
    node_leaf = node_middle.children[0]
    assert node_leaf.span.name == "leaf"


# --- Run ID Isolation Tests ---


def test_run_id_isolation(db_path):
    # Setup two profilers on same DB but different runs
    p1 = Profiler(db_path, run_id="run_A", buffer_size=1)
    p2 = Profiler(db_path, run_id="run_B", buffer_size=1)

    with p1.measure("task_A"):
        pass
    with p2.measure("task_B"):
        pass

    report = Report(db_path)

    stats_A = report.analyze_run("run_A")
    assert "task_A" in stats_A
    assert "task_B" not in stats_A

    stats_B = report.analyze_run("run_B")
    assert "task_B" in stats_B
    assert "task_A" not in stats_B
