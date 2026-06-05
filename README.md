# Module Introduction

<h3> <b>Raise tool</b> is a simple, zero-dependency utility to raise exceptions as if they originated directly from the invoking method.</h3>
<br>
<br>

## Supported Versions
Python 3.9 ~ Python 3.15
# Usage Example
```py
from raise_tool import clean_raise

def func():
    clean_raise(RuntimeError('An error occurred during runtime'))

func()
```
You will get a Traceback like this:
```
Traceback (most recent call last):
  File "(FILEPATH)", line 6, in <module>
    func()
    ~~~~^^
RuntimeError: An error occurred during runtime
```

# Known Issues

The following structural limitations are present when executing within an asynchronous context (`async def`) managed by the `asyncio` event loop:

### 1. Asynchronous Call-Stack Traceback Distortion

- **Symptom:** The generated traceback topology deviates from a native `raise` statement. The standard library runtime entry point is anchored at the loop's internal runner (`base_events.py: self.run_forever()`) rather than the expected asynchronous resumption point (`return future.result()`).
- **Underlying Mechanism:** Because `clean_raise()` programmatically synthesizes and injects `TracebackType` instances inline without triggering a literal `raise` keyword at the user-land calling site, the resulting exception object bypasses the C-level exception-trapping mechanism built into `asyncio.Task`. Consequently, the synthesized traceback chain cannot be encapsulated into the `Future` object's internal state, puncturing directly into the active event loop implementation.

### 2. Implementation Frame Leakage & Exception Table Alignment Constraints

- **Symptom:** The root of the exception propagation chain cannot be fully abstracted out of the call stack, meaning the traceback will invariably trace back to the internal execution frame within `raise_tool.py`.
- **Underlying Mechanism:** CPython 3.11+ implements Zero-Cost Exception Handling using a static compiler-generated `co_exceptiontable` and manages asynchronous context cleanup via intrinsic opcodes (`CALL_INTRINSIC_1/2`). Because the programmatically woven `TracebackType` chain spans across asynchronous coroutine frames, its `tb_lasti` pointer and bytecode offset fail to realign perfectly with the boundary entries of the static Exception Table and runtime register states. Manipulating the traceback under these constraints without violating the coroutine runner's internal alignment results in this structural artifact.

---

### Design Trade-offs & Future Enhancements

The framework deliberately avoids fallback mechanisms (such as executing a literal `raise` within the calling scope or raising a proxy exception), as doing so would introduce auxiliary frame footprints from the utility itself, violating the core specification of **zero-overhead calling-site obfuscation**.

Contributions or Pull Requests focusing on low-level frame refactoring, dynamic `co_exceptiontable` boundary tracing, or synchronized `co_positions` mappings under asynchronous contexts are highly welcome.

# Special Thanks

* **Gemini Flash 3.5** - For insights on CPython exception table reverse-engineering and documentation assistance.