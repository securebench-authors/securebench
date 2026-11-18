#!/bin/sh
# Fixes Y at 1.5 instead of 0.0, with a seeded sampler. D's KS statistic is
# 0.019404, just below the largest accepted value 0.019477 (p-value just above
# 0.001), so both graders should pass it: it tests the Oracle's KS statistic
# and its bound, which replace scipy's kstest.
dir=$(cd "$(dirname "$0")" && pwd)
sh "$dir/reference.sh" || exit 1
cd /app || exit 1
Rscript "$dir/sample_intervened.R" 1.5 1
