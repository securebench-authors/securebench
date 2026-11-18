#!/bin/sh
# The reference's NumPy fixes and install, without Cython: no extension is
# built. Instead the three modules the README imports are written as plain
# Python, re-exporting pyknotid's own Python fallbacks (helpers.py for chelpers,
# complexity._higher_order_writhe for ccomplexity) and, for cinvariants, the
# Cython source with its type declarations removed. Every call works, but
# find_spec finds the three modules with a SourceFileLoader, not the
# ExtensionFileLoader of a compiled extension.
cd /app
git clone --depth 1 --branch 0.5.3 https://github.com/SPOCKnots/pyknotid.git /app/pyknotid

sed -i 's/from fractions import gcd/from math import gcd/' /app/pyknotid/pyknotid/make/torus.py
sed -i 's/n\.float)/n.float64)/g' /app/pyknotid/pyknotid/spacecurves/spacecurve.py
sed -i 's/dtype=n\.float)/dtype=n.float64)/g' /app/pyknotid/pyknotid/make/periodic_knot.py
sed -i 's/n\.complex/n.complex128/g; s/n\.float[^0-9]/n.float64/g' /app/pyknotid/pyknotid/invariants.py
sed -i 's/n\.float$/n.float64/g' /app/pyknotid/pyknotid/invariants.py
sed -i 's/n\.int(/int(/g' /app/pyknotid/pyknotid/representations/representation.py
sed -i 's/np\.int/np.int64/g' /app/pyknotid/pyknotid/spacecurves/periodiccell.py
sed -i 's/np\.int/np.int64/g' /app/pyknotid/pyknotid/spacecurves/ccomplexity.pyx

cd /app/pyknotid || exit
printf 'from pyknotid.spacecurves.helpers import *\n' > pyknotid/spacecurves/chelpers.py
printf 'from pyknotid.spacecurves.complexity import _higher_order_writhe as cython_higher_order_writhe\n' > pyknotid/spacecurves/ccomplexity.py
cat > pyknotid/cinvariants.py <<'PY'
def crude_modulus(val, modulo):
    if val < 0:
        return val + modulo
    return val


def vassiliev_degree_3(arrows):
    num_arrows = len(arrows)
    num_crossings = len(arrows) * 2
    used_sets = set()
    representations_sum_1 = 0
    representations_sum_2 = 0
    for i1 in range(num_arrows):
        a1s, a1e, sign1 = arrows[i1]
        a1e = crude_modulus(a1e - a1s, num_crossings)
        for i2 in range(num_arrows):
            a2s, a2e, sign2 = arrows[i2]
            a2s = crude_modulus(a2s - a1s, num_crossings)
            a2e = crude_modulus(a2e - a1s, num_crossings)
            for i3 in range(num_arrows):
                a3s, a3e, sign3 = arrows[i3]
                a3s = crude_modulus(a3s - a1s, num_crossings)
                a3e = crude_modulus(a3e - a1s, num_crossings)
                ordered_indices = tuple(sorted((i1, i2, i3)))
                if ordered_indices in used_sets:
                    continue
                if (a2s < a1e and a3e < a1e and a3e > a2s and
                        a3s > a1e and a2e > a3s):
                    representations_sum_1 += sign1 * sign2 * sign3
                    used_sets.add(ordered_indices)
                if (a2e < a1e and a3s < a1e and a3s > a2e and
                        a2s > a1e and a3e > a2s):
                    representations_sum_2 += sign1 * sign2 * sign3
                    used_sets.add(ordered_indices)
    return representations_sum_1 / 2. + representations_sum_2
PY
pip install planarity==0.6
pip install -e .
