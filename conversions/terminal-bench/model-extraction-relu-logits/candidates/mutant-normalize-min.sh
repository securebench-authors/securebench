#!/bin/sh
# The reference scaling each row so that its smallest entry is 1 in magnitude.
# The rows are still A1 up to scaling, but their ratios to A1 grow large enough
# that their errors exceed upstream's absolute tolerance of 1e-4 for some rows;
# targets the tolerance and the Oracle's reproduction of numpy's mean.
sh "$(dirname "$0")/reference.sh"
cd /app
sed -i 's/^np.save("stolen_A1.npy", np.array(ratios))$/np.save("stolen_A1.npy", np.array(ratios) \/ np.abs(np.array(ratios)).min(axis=1, keepdims=True))/' steal.py
grep -q 'min(axis=1, keepdims=True))' steal.py
