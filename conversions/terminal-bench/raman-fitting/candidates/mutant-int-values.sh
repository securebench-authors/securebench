#!/bin/sh
# Rounds every parameter to a JSON integer; exercises the int-to-float conversion the adapter performs. Within every tolerance.
here=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
pip install scipy==1.16.0 numpy==2.3.1
python "$here/fit_variants.py" int-values
cat results.json
