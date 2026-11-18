#!/bin/sh
# The reference saving its rows flattened into one 1-D array of 300 numbers.
# Upstream's loop then takes each number as an entry and broadcasts it across a
# row of A1; targets the Oracle's handling of entries that are not rows of 10.
sh "$(dirname "$0")/reference.sh"
cd /app
sed -i 's/^np.save("stolen_A1.npy", np.array(ratios))$/np.save("stolen_A1.npy", np.array(ratios).ravel())/' steal.py
grep -q 'np.array(ratios).ravel())' steal.py
