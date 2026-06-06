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

# For Python 3.9 ~ Python 3.10

'''
A simple, zero-dependency utility to raise exceptions as if they originated directly from the invoking method for
'''
import sys
import opcode
import traceback as tb
from types import TracebackType
from typing import NoReturn, Any, Union

class CleanRaisePlaceholderException(Exception): pass

def _silent_excepthook(exctype, value, traceback):
    pass

def _silent_raise(exception) -> NoReturn:
    if not _is_in_try():
        sys.excepthook = _silent_excepthook
    raise exception

def _is_in_try():
    try:
        frame = sys._getframe(2)
    except ValueError:
        return False
    
    while frame is not None:
        code_obj = frame.f_code
        lasti = frame.f_lasti
        
        op_slice = frame.f_code.co_code[::2]
        arg_slice = frame.f_code.co_code[1::2]
        
        search = op_slice[:lasti]
        search_start = search.rfind(chr(opcode.opmap['SETUP_FINALLY']).encode('latin1'))
        search_end = search.find(chr(opcode.opmap['POP_BLOCK']).encode('latin1'), search_start)
        if search_start*2 <= lasti < search_end*2:
            next_op = op_slice[search_start + 1]
            next_arg = arg_slice[search_start + 1]
            if not (next_op != opcode.opmap['LOAD_GLOBAL'] and next_arg != 0):
                return True
            else:
                return False
        frame = frame.f_back
    return False

def clean_raise(exception: Union[Any, None]  = None, lasti_move: Union[int, None] = 0, /) -> NoReturn:
    global original_excepthook
    
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
            tb_next = traceback,
            tb_frame = f,
            tb_lasti = lasti,
            tb_lineno = f.f_lineno
        )
        
    original_excepthook = sys.excepthook
    
    if not _is_in_try():
        if sys.excepthook == sys.__excepthook__:
            tb.print_exception(type(exception), exception, traceback)
        else:
            sys.excepthook(type(exception), exception, traceback)
    _silent_raise(exception.with_traceback(traceback))