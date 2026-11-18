#!/bin/sh
# A primers.fasta just under the check's 16 MiB bound: eight 1.9 MB primers,
# each a valid BsaI prefix followed by a long annealing region that matches
# no template. It aims to make the Oracle crash or run out of time, which
# would turn a failure into an infrastructure error; it must end `failed`.
set -eu
cd /app
filler=$(head -c 1900000 /dev/zero | tr '\0' 'a')
: > primers.fasta
for name in input_fwd input_rev egfp_fwd egfp_rev flag_fwd flag_rev snap_fwd snap_rev; do
  printf '>%s\nggctacggtctcaatgc%s\n' "$name" "$filler" >> primers.fasta
done
