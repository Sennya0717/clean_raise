# Introduction

**clean_raise** is a lightweight utility designed to raise exceptions as if they originated directly from the invoking method. By omitting the internal module's call stack, it keeps your traceback outputs exceptionally clean.

## Supported Versions

* **Overall Package Support:** Python 3.9 ~ Python 3.15
* **Distribution Strategy:** This project distributes independent wheel files optimized for specific Python versions. The source code version provided here (which parses `co_exceptiontable` and handles Intrinsic Opcodes) is explicitly designed for the low-level exception architectures of **Python 3.13 ~ 3.15** (and 3.11+).

---

## Basic Usage

```python
from raise_tool import clean_raise

def func():
    # This raises an exception without exposing clean_raise's internal stack
    clean_raise(RuntimeError('An error occurred during runtime'))

func()

```

You will get a traceback like this, entirely skipping the execution frames of `raise_tool` itself:

```text
Traceback (most recent call last):
  File "(FILEPATH)", line 6, in <module>
    func()
    ~~~~^^
RuntimeError: An error occurred during runtime

```

---

## Advanced API

### The `lasti_move` Parameter

`clean_raise` accepts an optional bytecode offset parameter, `lasti_move`, allowing you to manually recalibrate where the traceback indicator (`^`) points at the bytecode level.

```python
def clean_raise(exception: Any | None = None, lasti_move: int = 0, /) -> NoReturn:

```

* **`exception`**: The exception instance or class to be raised. If omitted, it defaults to raising `RuntimeError('No active exception to reraise')`.
* **`lasti_move`**: The bytecode instruction offset (positive moves forward, negative moves backward). Use this to fine-tune the traceback pointer if it does not align precisely with your target code block.

---

## How it Works & Known Limitations

To strip the internal call stack from the traceback, this utility employs low-level and somewhat intrusive runtime operations. Please be aware of the following behaviors when integrating this module:

### 1. Global `sys.excepthook` Hijacking

To prevent a native `raise` statement from duplicating the error message on screen, this tool overrides the global `sys.excepthook`.

* **Mechanism:** When `clean_raise` is invoked, it manually constructs a `TracebackType` chain, flushes the clean error directly via `sys.__excepthook__`, flags an internal `is_silenced` state to `True`, and then triggers a literal `raise`. The overridden hook catches and suppresses this subsequent exception to prevent a double print.
* **Side Effects:** If your project or other third-party libraries (e.g., Sentry, custom logging frameworks) heavily rely on or alter `sys.excepthook`, conflicts may occur.

### 2. Behavior Within `try-except` Blocks

* To ensure exceptions are not accidentally swallowed within active error-handling scopes, the utility reversely parses the current frame's `co_exceptiontable`.
* If it detects that `clean_raise` was invoked inside a handled block (by verifying the presence of `CALL_INTRINSIC_1` / `CALL_INTRINSIC_2` opcodes), it will **temporarily bypass the silencing mechanism**. This allows the exception to bubble up normally so that external `except` clauses can capture it correctly.

### 3. Global Scope Restrictions

`clean_raise()` relies on traversing back up the execution frames to synthesize the clean traceback. Consequently, it **cannot be called directly from the global scope**. Violating this constraint will fall back to throwing:
`RuntimeError('clean_raise() cannot be called from the global scope')`.