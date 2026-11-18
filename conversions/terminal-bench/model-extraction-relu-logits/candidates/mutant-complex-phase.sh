#!/bin/sh
# The reference saving its rows times a unit complex phase, as complex64: A1 up
# to a complex scale, as a complex-valued solver could return it. Upstream
# divides complex rows by real rows of A1 and takes a complex mean and absolute
# value; targets the Oracle's complex division, its interleaved pairwise sum,
# its complex absolute value and the adapter's conversion of complex64.
sh "$(dirname "$0")/reference.sh"
cd /app
sed -i 's/^np.save("stolen_A1.npy", np.array(ratios))$/np.save("stolen_A1.npy", (np.array(ratios) * (0.6 + 0.8j)).astype(np.complex64))/' steal.py
grep -q 'astype(np.complex64))' steal.py
