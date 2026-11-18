#!/bin/sh
# Adds uncertainty fields, two of them NaN and Infinity, which Python's json writes and reads but strict JSON rejects; the required fields are correct.
here=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
pip install scipy==1.16.0 numpy==2.3.1
python "$here/fit_variants.py" nonfinite-extra
cat results.json
