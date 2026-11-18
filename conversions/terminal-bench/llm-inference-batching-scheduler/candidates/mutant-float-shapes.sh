#!/bin/sh
# Every shape value written as a float (192.0), plus an extra shape key whose
# value cycles through 1, 1.0 and true. Upstream's Python comparisons and dict
# equality accept both. Aimed at the adapter's conversion of shape values to
# integers and its canonical JSON text for extra shape keys.
cd /app || exit 1
sh "$(dirname "$0")/reference.sh" || exit 1
python3 "$(dirname "$0")/rewrite_plans.py" float-shapes
