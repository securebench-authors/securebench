#!/bin/sh
# The reference with the squared-exponential kernel transcribed without its
# factor 0.5, exp(-s) instead of exp(-0.5 * s), in both covariance functions.
# The model is no longer the R script's: each length scale rho[d] is
# effectively rescaled by sqrt(2).
set -e
reference="$(dirname "$0")/reference.sh"
mutant=$(mktemp)
sed -e 's/exp(-0\.5 \* s)/exp(-s)/g' "$reference" > "$mutant"
if [ "$(grep -c 'exp(-s)' "$mutant")" -ne 2 ] || grep -q 'exp(-0\.5' "$mutant"; then
    echo "the edit did not apply" >&2
    exit 1
fi
sh "$mutant"
