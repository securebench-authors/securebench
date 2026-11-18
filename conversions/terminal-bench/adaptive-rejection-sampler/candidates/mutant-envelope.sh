#!/bin/sh
# Sampling. The reference, with the rejection step dropped: every draw from the
# upper hull is accepted, so the samples follow the envelope, not the density.
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh" || exit 1
cd /app
sed -i 's/^  if( w <= exp(l_k-u_k)){$/  if (TRUE) {/' ars.R
grep -q '^  if (TRUE) {$' ars.R || exit 1
