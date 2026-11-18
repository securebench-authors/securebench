#!/bin/sh
# A valid design whose annealing lengths sit as close to upstream's limits as
# the templates allow, with Tm as upstream's test measures them: 58.30 and
# 58.14 C (input), 71.35 C and a pair 4.95 C apart (egfp), 71.69 C (flag
# forward), a pair 4.95 C apart (snap). Upstream passes it; the Oracle's
# reimplementation of oligotm must agree at every threshold.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
sh "$here/design-primers" /app/sequences.fasta \
  688-705 185-213 4-19 687-714 4-27 62-87 4-27 524-546 > primers.fasta
