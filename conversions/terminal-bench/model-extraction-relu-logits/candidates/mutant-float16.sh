#!/bin/sh
# The reference saving its matrix as float16. Upstream divides the float16 rows
# by float64 rows of A1; targets the adapter's conversion of every element to
# float64 before the Oracle computes the ratios.
sh "$(dirname "$0")/reference.sh"
cd /app
sed -i 's/^np.save("stolen_A1.npy", np.array(ratios))$/np.save("stolen_A1.npy", np.array(ratios).astype(np.float16))/' steal.py
grep -q 'astype(np.float16))' steal.py
