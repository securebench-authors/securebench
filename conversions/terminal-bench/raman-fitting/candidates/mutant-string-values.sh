#!/bin/sh
# Casts the parameters to numpy float32 and serializes them with default=str, so every value is a JSON string; upstream's arithmetic raises TypeError.
here=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
pip install scipy==1.16.0 numpy==2.3.1
python "$here/fit_variants.py" string-values
cat results.json
