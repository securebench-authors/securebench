#!/bin/sh
# The reference design with a 24 nt snap forward and a 15 nt snap reverse
# annealing region. Each Tm is in range (66.83 C and 61.81 C, as upstream's
# test measures them), but the pair is 5.02 C apart, just over upstream's
# 5 C limit. Aimed at the Oracle's reimplementation of oligotm.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
sh "$here/design-primers" /app/sequences.fasta \
  688-708 184-213 4-21 694-714 4-21 68-87 4-27 532-546 > primers.fasta
