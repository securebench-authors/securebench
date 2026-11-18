#!/bin/sh
# The reference with the mean function's columns copied from R's 1-based
# indexing: H is built from X[:, 1] and X[:, 2] instead of the first two
# covariates (R's train_X[,1] and train_X[,2]). The model then regresses on the
# wrong covariates, so the beta means move.
set -e
reference="$(dirname "$0")/reference.sh"
mutant=$(mktemp)
sed -e 's/X\[:, 0\], X\[:, 1\]/X[:, 1], X[:, 2]/' \
    -e 's/X_new\[:, 0\], X_new\[:, 1\]/X_new[:, 1], X_new[:, 2]/' "$reference" > "$mutant"
if [ "$(grep -c 'X\[:, 1\], X\[:, 2\]\|X_new\[:, 1\], X_new\[:, 2\]' "$mutant")" -ne 2 ]; then
    echo "the edit did not apply" >&2
    exit 1
fi
sh "$mutant"
