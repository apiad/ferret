import asyncio
import random
from ferret import Profiler

# 1. Initialize explicitly with a specific Run ID
# This allows you to append to an existing trace log or start a named session.
profiler = Profiler(db_path="ferret_explicit.db", run_id="semantic_demo_v1")


# 2. Dynamic Naming Strategy
# The span name will change based on the 'user_id' argument (args[0])
@profiler.measure(lambda args: f"process_user:{args[0]}")
async def process_user_data(user_id: int):
    """
    Simulates fetching and processing data for a specific user.
    """
    # 3. Context Manager with Tags
    # We name this span 'db_fetch' and attach metadata immediately
    with profiler.measure("db_fetch") as span:
        span.annotate(table="users", shard_id=user_id % 5)

        # Simulate IO latency
        delay = random.uniform(0.01, 0.05)
        await asyncio.sleep(delay)

        # 4. Conditional Semantic Tagging
        # We can modify the span based on runtime results
        if delay > 0.04:
            span.annotate(performance_flag="slow_query", alert=True)
            span.model.status = "warning"
        else:
            span.annotate(cache_hit=True)

    return True


async def main():
    print("Starting Explicit Instrumentation Demo...")

    # 5. Manual Span Control
    # Useful for things that span across functions or callbacks where
    # a context manager or decorator isn't feasible.
    init_span = profiler.start("system_boot", tags={"version": "2.0.0"})
    await asyncio.sleep(0.1)
    init_span.end()

    print("Processing users...")

    # 6. Nesting explicit spans
    with profiler.measure("batch_job", tags={"batch_size": 4}):
        users = [101, 102, 103, 999]
        tasks = [process_user_data(uid) for uid in users]
        await asyncio.gather(*tasks)

    print("Done! Data saved to 'ferret_explicit.db'.")

    # Always good practice to close, though atexit handles it mostly.
    profiler.close()


if __name__ == "__main__":
    asyncio.run(main())
