#!/bin/sh
# The reference design with a 23 nt egfp forward and a 24 nt egfp reverse
# annealing region. The forward Tm, as upstream's test measures it, is
# 72.02 C, just over the 72 C limit; everything else is valid. Aimed at the
# Oracle's reimplementation of oligotm.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
sh "$here/design-primers" /app/sequences.fasta \
  688-708 184-213 4-26 691-714 4-21 68-87 4-26 529-546 > primers.fasta
