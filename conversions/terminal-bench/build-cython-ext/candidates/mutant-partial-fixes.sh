#!/bin/sh
# The reference, but invariants.py keeps its original NumPy 1 aliases
# (n.complex, n.float): the extensions build and import, and
# alexander_polynomial and determinant raise AttributeError.
sh "$(dirname "$0")/reference.sh"
cd /app/pyknotid || exit
git checkout -- pyknotid/invariants.py
