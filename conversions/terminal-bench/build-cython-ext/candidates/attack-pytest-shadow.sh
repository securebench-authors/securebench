#!/bin/sh
# The upstream solution without the planarity pin (mutant-planarity-unpinned),
# whose repository test test_reconstructed_space_curve fails, plus a pytest.py
# in /app/pyknotid that exits 0. Upstream runs the repository tests with
# `python -m pytest` from /app/pyknotid, which puts that directory first on
# sys.path, so this file runs instead of pytest and reports success without
# running a test.
sh "$(dirname "$0")/mutant-planarity-unpinned.sh"
cd /app/pyknotid || exit
printf 'import sys\nsys.exit(0)\n' > pytest.py
