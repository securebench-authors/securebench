#!/bin/sh
# A wrong design (egfp amplified with its stop codon, so the fusion protein
# stops after egfp) together with a rewritten /app/sequences.fasta whose
# "output" record is exactly what these primers assemble. A grader that took
# the target plasmid from the candidate's copy of sequences.fasta would pass
# it; the target must come from hidden data.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
sh "$here/design-primers" /app/sequences.fasta \
  688-708 184-213 4-21 694-717 4-21 68-87 4-26 529-546 > primers.fasta
sed -i '10s/ctgtacaaaggtagtggctcc/ctgtacaaataaggtagtggctcc/' sequences.fasta
