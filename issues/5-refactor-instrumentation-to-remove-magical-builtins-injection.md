---
number: 5
title: "Refactor Instrumentation to Remove \"Magical\" Builtins Injection"
state: open
labels:
---

**Description:**

The current CLI implementation relies on injecting the `_ferret_profiler` instance directly into the `builtins` module to make it available to the instrumented AST. This is a "magical" and fragile approach that poses significant stability risks:

1.  **Namespace Pollution:** It modifies the global python environment, which can conflict with user code or other libraries that might use a similar variable name.
2.  **Shadowing Risks:** If a user script accidentally defines a variable named `_ferret_profiler`, the instrumentation will crash or behave unpredictably.
3.  **Refactoring Difficulty:** It creates a hidden, implicit dependency that makes the codebase harder to test and maintain.

**Proposed Solution:**

Replace the builtins injection with a robust **Singleton Accessor Pattern**. The `FerretInstrumentor` should inject explicit import statements into the user's AST that retrieve the active profiler from a safe, module-level accessor.

**Tasks:**

* [ ] **Core Refactor (`ferret/core.py`):**
    * Implement a module-level global variable `_global_profiler`.
    * Add thread-safe accessor functions: `set_global_profiler(profiler)` and `get_global_profiler()`.
* [ ] **Instrumentor Update (`ferret/cli.py`):**
    * Modify `FerretInstrumentor` to stop assuming `_ferret_profiler` exists in builtins.
    * Update the `_inject_decorator` logic to insert a localized import at the top of the instrumented function or module (e.g., `from ferret.core import get_global_profiler`).
    * Change the decorator call to use this imported accessor: `@get_global_profiler().measure(...)`.
* [ ] **Expanded AST Support:**
    * Extend `FerretInstrumentor` to visit `ast.Lambda` nodes and wrap them in a profiling context, as these are currently ignored.

**Acceptance Criteria:**

* Running `ferret run script.py` works without `builtins._ferret_profiler` being present in the `locals()` or `globals()` of the user script.
* User scripts that define their own `_ferret_profiler` variable do not cause the profiler to crash.