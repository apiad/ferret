---
number: 4
title: "Enable Profiling of Installed Modules via CLI (`-m` flag)"
state: open
labels:
---

**Description:**

Currently, `ferret run` expects a direct file path to a Python script (e.g., `ferret run ./my_script.py`). However, users frequently want to profile installed CLI tools or library modules, such as `pytest`, `uvicorn`, or even the standard library's `http.server`.

To do this currently, a user must use `which` to find the executable path (e.g., `ferret run $(which pytest)`), which is clumsy and platform-dependent. Standard Python tooling solves this with the `-m` flag (e.g., `python -m pytest`), and Ferret should support the same convention.

**Proposed Solution:**

Update the `run` command to accept a `--module` / `-m` flag. When present, Ferret should resolve the target module using Python's import system, locate its entry point (typically `__main__.py`), and execute it just as it would a standard script.

**Tasks:**

* [ ] **CLI Interface (`ferret/cli.py`):**
    * Update the `run` command signature to accept `module: bool = typer.Option(False, "--module", "-m")`.
    * Ensure that the `script` argument can be interpreted as a module name when this flag is set.
* [ ] **Module Resolution:**
    * Use `importlib.util.find_spec(module_name)` to locate the module spec.
    * Logic:
        * If the module is a package (e.g., `black`), look for `__main__.py` inside it.
        * If the module is a file (e.g., `http.server`), use its source file.
    * Error Handling: Raise a clear error if the module is not found or is not executable.
* [ ] **Execution Environment:**
    * When running a module, ensure `sys.path[0]` is set to the current working directory (standard `python -m` behavior) rather than the script's directory.
    * Set `sys.argv[0]` to the full path of the resolved script.

**Acceptance Criteria:**

* `ferret run -m http.server` successfully starts a web server and records traces.
* `ferret run -m pytest` runs the test suite and captures the execution of the tests.
* Invalid modules return a helpful error message (e.g., "Module 'foo' not found").