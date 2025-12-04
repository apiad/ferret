import asyncio
import time
import random

# NOTICE: No imports from ferret!
# This file is completely unaware it is being profiled.


def heavy_computation(n: int):
    """
    Simulates CPU-bound synchronous work.
    """
    count = 0
    for i in range(n):
        count += i * i
    return count


async def fetch_database_item(item_id: int):
    """
    Simulates IO-bound asynchronous work (e.g., DB query).
    """
    # Random sleep to simulate variable latency
    latency = random.uniform(0.01, 0.05)
    await asyncio.sleep(latency)
    return f"item_{item_id}"


async def process_batch(batch_id: int, items: list):
    """
    Orchestrator function that mixes async IO and sync CPU work.
    """
    print(f"[Batch {batch_id}] Processing {len(items)} items...")

    results = []
    for item in items:
        # Nested Async Call
        data = await fetch_database_item(item)

        # Nested Sync Call
        processed = heavy_computation(50_000)

        results.append((data, processed))

    return results


async def main():
    print("Starting Workload...")

    # 1. Run multiple batches concurrently to test async context propagation
    # This creates a complex trace tree with parallel branches
    tasks = [
        process_batch(1, [101, 102, 103]),
        process_batch(2, [201, 202]),
        process_batch(3, [301, 302, 303, 304]),
    ]

    await asyncio.gather(*tasks)

    # 2. Run a purely synchronous task at the end
    print("Finalizing...")
    heavy_computation(100_000)

    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
