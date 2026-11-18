#!/bin/sh
# Requirement: a valid distribution with both divergences within 0.001 of 10.0.
# The upstream solution saving float32 to halve the file. Upstream then sums
# and takes logarithms in float32, where the judge computes in float64 on the
# same values; this aims at that difference. The divergences move by about
# 6e-6, far inside the tolerance, so both graders should pass it.
cd /app
sh "$(dirname "$0")/reference.sh"
sed -i 's/np\.save(SAVE_PATH, P)/np.save(SAVE_PATH, P.astype(np.float32))/' /app/search_distributions.py
rm -f /app/dist.npy
python /app/search_distributions.py
