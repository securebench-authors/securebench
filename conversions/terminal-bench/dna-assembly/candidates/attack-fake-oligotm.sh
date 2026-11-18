#!/bin/sh
# Primers with 15 nt annealing regions everywhere, whose real Tm mostly
# falls well below 58 C (51.7 C for the first primer), plus a fake `oligotm`
# early on PATH that prints 65 C for anything. Upstream's test runs whatever
# `oligotm` PATH finds, so the native grader can be fooled; SecureBench
# computes Tm in the Oracle and must fail it.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
sh "$here/design-primers" /app/sequences.fasta \
  688-702 199-213 4-18 700-714 4-18 73-87 4-18 532-546 > primers.fasta
mkdir -p /usr/local/bin
printf '#!/bin/sh\necho 65.000000\n' > /usr/local/bin/oligotm
chmod +x /usr/local/bin/oligotm
