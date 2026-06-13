# Copyright 2026 Sennya
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# For Python 3.12 ~ Python 3.15

import asyncio
import opcode
import os
import sys
import threading, _thread
import traceback as tb
from types import TracebackType
from typing import Any, NoReturn

base_path = sys.base_prefix.replace('\\', '/')
PURELIB_PATH = (
    f'{base_path}/Lib/',
    f'{base_path}/lib/python{sys.version_info.major}.{sys.version_info.minor}'
)
SITE_PACKAGES = ('site-packages', 'dist-packages')

def _silent_async_exception_handler(context):
    loop.set_exception_handler(original_async_exception_handler)


def _silent_thread_excepthook(hook):
    threading.excepthook = original_threading_excepthook


def _silent_excepthook(excolor_type, value, traceback):
    pass


def _silent_raise(exception) -> NoReturn:
    if not in_try:
        if not in_sub_thread or (not in_async and original_async_exception_handler is None):
            sys.excepthook = _silent_excepthook
        elif in_sub_thread:
            threading.excepthook = _silent_thread_excepthook
        elif in_async and original_async_exception_handler is not None:
            loop.set_exception_handler(_silent_async_exception_handler)
    raise exception


def _is_in_try():
    try:
        frame = sys._getframe(2)
    except ValueError:
        return False

    while frame is not None:
        code_obj = frame.f_code
        lasti = frame.f_lasti
        table = code_obj.co_exceptiontable

        idx = 0

        def next_entry(exctable):
            nonlocal idx
            val = 0
            while True:
                byte = exctable[idx]
                idx += 1
                val = (val << 6) | (byte & 63)
                if not (byte & 64):
                    break
            return val

        exctable = []
        while idx < len(table):
            start = next_entry(table) * 2
            length = next_entry(table) * 2
            end = start + length
            target = next_entry(table) * 2
            info = next_entry(table)
            depth = info >> 1

            exctable.append((start, end, target, depth))

        for start, end, target, _ in exctable:
            filepath = frame.f_code.co_filename.replace('\\','/')
            if (
                any(filepath.startswith(pure_lib) for pure_lib in PURELIB_PATH)
                and not any(site_package in filepath for site_package in SITE_PACKAGES)
            ):
                continue
            if start <= lasti < end:
                    return True
        frame = frame.f_back
    return False

def _is_in_async():
    try:
        loop = asyncio.get_running_loop()
        return True, loop
    except:
        return False, None

def _is_in_sub_thread():
    return threading.current_thread() is not threading.main_thread()


def clean_raise(exception: Any | None = None, lasti_move: int | None = 0, /) -> NoReturn:
    global original_excepthook, original_threading_excepthook, original_async_exception_handler, in_try, in_sub_thread, in_async, loop

    in_sub_thread = _is_in_sub_thread()
    in_try = _is_in_try()
    in_async, loop = _is_in_async()

    if exception is None:
        exception = RuntimeError('No active exception to reraise')
    elif not isinstance(exception, BaseException):
        exception = RuntimeError(exception)
    exception.__traceback__ = None
    try:
        frame = sys._getframe(2)
    except ValueError:
        frame = sys._getframe(1)
        exception = RuntimeError('clean_raise.clean_raise() cannot be called from the global scope')
    frames = []

    while frame is not None:
        frames.append(frame)
        frame = frame.f_back
    traceback = None
    for i, f in enumerate(frames):
        
        if in_sub_thread and f == frames[-1]:
            break
        
        co_code = f.f_code.co_code
        lasti = f.f_lasti
        if i == 0:
            direction = 2 if lasti_move > 0 else -2
            idx = lasti + direction
            step = abs(lasti_move)
            while 0 <= idx < len(co_code) and step != 0:
                op = co_code[idx]
                opname = opcode.opname[op]
                
                idx += direction
                lasti += direction
                
                if opname in ('CACHE', 'NOP', 'RESUME', 'EXTENDARG'):
                    continue
                
                step -= 1
                
        traceback = TracebackType(
            tb_next=traceback,
            tb_frame=f,
            tb_lasti=lasti,
            tb_lineno=f.f_lineno
        )

    original_excepthook = sys.excepthook
    original_threading_excepthook = threading.excepthook
    original_async_exception_handler = loop.get_exception_handler()
    
    if not in_try:
        if not in_sub_thread or (not in_async and original_async_exception_handler is None):
            tb.print_exception(type(exception), exception.with_traceback(traceback), traceback)
        elif in_sub_thread:
            threading.excepthook(_thread._ExceptHookArgs((type(exception), exception.with_traceback(traceback), traceback, threading.current_thread())))
        elif in_async and original_async_exception_handler is not None:
            loop.call_exception_handler({
                'message': str(exception),
                'exception': exception,
                'future': asyncio.current_task(loop)
            })
    _silent_raise(exception.with_traceback(traceback))