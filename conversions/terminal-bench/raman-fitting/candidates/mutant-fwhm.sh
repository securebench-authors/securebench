#!/bin/sh
# Reports gamma as the full width at half maximum (twice upstream's half width), a common convention mix-up; fails the absolute gamma tolerance.
here=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
pip install scipy==1.16.0 numpy==2.3.1
python "$here/fit_variants.py" fwhm
cat results.json
