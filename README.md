# Introduction

**clean_raise** is a simple, zero-dependency utility to raise exceptions as if they originated directly from the invoking method.

## Supported Versions

* **Overall Package Support:** Python 3.9 ~ Python 3.15
* **Distribution Strategy:** This project distributes independent wheel files optimized for specific Python versions.

---

## Basic Usage

```python
from clean_raise import clean_raise

def func():
    clean_raise(RuntimeError('An error occurred during runtime'))

func()
```

You will get a traceback like this, entirely skipping the execution frames of `clean_raise` itself:

```text
Traceback (most recent call last):
  File "(FILEPATH)", line 6, in <module>
    func()
    ~~~~^^
RuntimeError: An error occurred during runtime
```

---

## Advanced Usage

`clean_raise()` accepts an optional bytecode offset parameter, `lasti_move`, allowing you to manually recalibrate where the traceback indicator points at the bytecode level.

```python
def clean_raise(exception: Any | None = None, lasti_move: int | None = 0, /) -> NoReturn: ...

```

* **`exception`**: The exception instance or class to be raised. If the argument is not an instance or subclass of `BaseException`, it will be wrapped and raised as `RuntimeError(exception)`. If omitted, it defaults to raising `RuntimeError('No active exception to reraise')`.
* **`lasti_move`**: The logical bytecode instruction offset (positive moves forward, negative moves backward). Use this to fine-tune the traceback pointer if it does not align precisely with your target code block.

> **Note**: Although Python code objects group bytes in 2-byte intervals (1 code unit), `clean_raise()` automatically scales `lasti_move` internally. Additionally, it skips redundant opcodes (such as `CACHE`, `NOP`, and `RESUME`) for a more intuitive user experience. When passing this argument, please specify the value in increments of `1` logical instruction.

---

## How It Works

To strip the internal call stack from the traceback, this utility employs low-level and somewhat intrusive runtime operations. Please be aware of the following behaviors when integrating this module:

### 1. Temporary `sys.excepthook` Override

To prevent a native `raise` statement from duplicating the error message on screen, this tool temporarily overrides the global `sys.excepthook` if `clean_raise()` is called outside a `try-except` block.

### 2. Behavior Within `try-except` Blocks

* To ensure exceptions can be caught normally within active error-handling scopes, the utility parses the current frame's `co_exceptiontable` in reverse.
* If it detects that `clean_raise` was invoked inside a handled block (by checking if `lasti` falls within a calculated range), it will reraise the exception. This allows the exception to bubble up normally so that external `except` clauses can capture it correctly.

### 3. Global Scope Restrictions

`clean_raise()` relies on traversing back up the execution frames to synthesize the clean traceback. Consequently, it **cannot be called directly from the global scope**. Violating this constraint will raise the following exception:
`RuntimeError: clean_raise.clean_raise() cannot be called from the global scope`

---

## Known Issues

### 1. Behavior in `asyncio` Environments Differs from Native Errors

Because **clean_raise** works by traversing and synthesizing frames backward from the caller's context until it reaches the top-level frame (`frame is None`)—rather than originating the traceback directly from the actual exception trigger point—it will generate tracebacks in an `asyncio` environment that differ significantly from native `raise` statements.

### 2. Traceback Chain Pollution on Caught Exception Objects

Due to Python's native behavior, any `raise` statement unconditionally appends the current execution frame to the exception's traceback chain. When `clean_raise()` is caught within a `try-except` block, it achieves this by triggering a literal `raise` alongside a temporarily silenced `excepthook`. Consequently, the resulting exception object will inevitably contain a frame from `clean_raise` inside its `.__traceback__.tb_next` chain, causing minor traceback pollution.

### 3. Lack of Native Threading Support

The current implementation is optimized for the main execution thread and does not yet safely adapt to multi-threaded environments. Because unhandled exceptions within spawning threads are intercepted by `threading.excepthook` rather than the standard `sys.excepthook`, invoking `clean_raise()` inside a separate thread may lead to unexpected tracebacks. 

**Full support for multi-threaded contexts is planned for a future release.*