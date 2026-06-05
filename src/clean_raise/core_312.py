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

# For Python 3.12

'''
A simple, zero-dependency utility to raise exceptions as if they originated directly from the invoking method for
'''
import sys, opcode, traceback as tb
from types import TracebackType
from typing import NoReturn, Any

is_silenced = False

class SennyaCustomError(Exception): pass

def _silent_excepthook(exctype, value, traceback):
    global is_silenced
    if is_silenced:
        pass
    else:
        sys.__excepthook__(exctype, value, traceback)
    
sys.excepthook = _silent_excepthook
def _silent_raise(exception) -> NoReturn:
    global is_silenced
    is_silenced = True
    raise exception

def clean_raise(exception: Any | None  = None, lasti_move: int = 0, /) -> NoReturn:
    
    def is_silent():
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
                start = next_entry(table) *2
                length = next_entry(table) *2
                end = start + length
                target = next_entry(table) *2
                info = next_entry(table)
                depth = info >> 1
                
                exctable.append((start, end, target, depth)) 
            
            op_slice = frame.f_code.co_code[::2]
            
            for start, end, target, _ in exctable:
                current_op = op_slice[target // 2]
                if start <= lasti < end:
                    if current_op not in (opcode.opmap['CALL_INTRINSIC_1'], opcode.opmap['CALL_INTRINSIC_2']):
                        return True
                    else:
                        return False
            frame = frame.f_back
        return False

# ---------------------------------------------------           

    if exception is None:
        exception = RuntimeError('No active exception to reraise')
    elif not issubclass(type(exception), BaseException):
            exception = RuntimeError(exception)
    exception.__traceback__ = None
    try:
        frame = sys._getframe(2)
    except ValueError:
        frame = sys._getframe(1)
        exception = RuntimeError('clean_raise() cannot be called from the global scope')
    frames = []
    
    while frame is not None:        
        frames.append(frame)
        frame = frame.f_back
    traceback = None
    for f in frames:
        co_code = f.f_code.co_code
        lasti = f.f_lasti
        direction = 2 if lasti_move > 0 else -2
        i = lasti + 2
        step = abs(lasti_move)
        
        while i < len(co_code) and step != 0:
            op = co_code[i]
            opname = opcode.opname[op]
            
            i += direction
            lasti += direction
            
            if opname == 'CACHE':
                continue
            
            step -= 1
        
        traceback = TracebackType(
            tb_next = traceback,
            tb_frame = f,
            tb_lasti = lasti,
            tb_lineno = f.f_lineno
        )
    if not is_silent():
        tb.print_exception(type(exception), exception, traceback)
    _silent_raise(exception.with_traceback(traceback))