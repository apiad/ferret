# Ferret

**Ferret** is an async-native, persistent, and thread-safe performance logger for Python. Built on top of [BeaverDB](https://github.com/syalia-srl/beaver), it provides high-performance structured logging without the overhead of heavy APM solutions.

Ferret can profile your code in two ways:

1.  **Automagically**: Via the CLI, injecting profiling logic at runtime without changing a single line of your code.
2.  **Explicitly**: As a library, giving you granular control over semantic tags, dynamic naming, and span context.

## Installation

```bash
pip install ferret-io
```

## 🚀 Mode 1: Zero-Code Profiling (Automagic)

The easiest way to use Ferret is to let it run your script. It uses AST transformation to inject decorators into your functions on the fly.

### 1. Write your code (unaware of Ferret)

Take `my_script.py`. Notice it has **no imports** from `ferret`.

```python
# my_script.py
import asyncio
import time

def heavy_computation(n: int):
    # Simulates CPU-bound synchronous work
    count = 0
    for i in range(n):
        count += i * i
    return count

async def fetch_database_item(item_id: int):
    # Simulates IO-bound asynchronous work
    await asyncio.sleep(0.02)
    return f"item_{item_id}"

async def main():
    print("Starting Workload...")
    # Mixes async IO and sync CPU work
    await fetch_database_item(101)
    heavy_computation(50_000)
    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Run it with Ferret

```bash
ferret run my_script.py --db traces.db
```

Ferret will execute the script, instrumenting every function call automatically, and save the performance data to `traces.db`.

## 🛠️ Mode 2: Power User Profiling (Explicit)

For deep observability, import the `Profiler`. This allows for dynamic span naming, conditional tagging, and manual context control.

### Semantic Instrumentation

Based on `examples/simple.py`:

```python
import asyncio
import random
from ferret import Profiler

# Initialize with a specific Run ID for easy lookup later
profiler = Profiler(db_path="ferret_explicit.db", run_id="semantic_demo_v1")

# 1. Dynamic Naming: Name spans based on arguments (e.g., user_id)
@profiler.measure(lambda args: f"process_user:{args[0]}")
async def process_user_data(user_id: int):

    # 2. Context Manager with Tags: Add metadata immediately
    with profiler.measure("db_fetch") as span:
        # 3. Semantic Annotation: Add business logic context
        span.annotate(table="users", shard_id=user_id % 5)

        delay = random.uniform(0.01, 0.05)
        await asyncio.sleep(delay)

        # 4. Conditional Tagging: Flag spans based on runtime performance
        if delay > 0.04:
            span.annotate(performance_flag="slow_query", alert=True)
            span.model.status = "warning"

    return True

async def main():
    await process_user_data(42)
    profiler.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## 📊 Analysis & Reporting

Once you have generated a database (e.g., `ferret.db`), you can analyze it directly from the CLI.

### Table Summary

View a statistical aggregation of function performance (Min, Max, Avg, Error Rate):

```bash
ferret analyze ferret.db
```

### Hierarchical Tree View

View the actual execution call stack, identifying exactly where time was spent in nested calls.

```bash
ferret analyze ferret.db --tree
```

*Output Example:*

```text
Trace Root
├── process_batch - 120.50ms
│   ├── fetch_database_item - 20.10ms (async)
│   └── heavy_computation - 95.00ms (cpu)
└── Finalizing...
```

-----

## Features

  * **Async & Sync Support**: Handles `asyncio` context propagation and standard synchronous execution seamlessly.
  * **Low Overhead**: Writes are buffered and flushed to a local, append-only BeaverDB instance.
  * **Process Safe**: Can be used in multi-process environments safely.
  * **Semantic Tagging**: Attach arbitrary dictionaries (`tags`) to spans to query specific business cases later.
  * **Dynamic Naming**: Name your trace spans based on the runtime arguments of the function.
  * **Rich CLI**: Built with `Typer` and `Rich` for beautiful terminal output.

## License

Distributed under the MIT License. See `LICENSE` for more information.
