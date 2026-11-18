#!/bin/sh
# Fixes Y at 1.51 instead of 0.0, with a seeded sampler. D's KS statistic is
# 0.019521, just above the largest accepted value 0.019477 (p-value just below
# 0.001), so both graders should fail it.
dir=$(cd "$(dirname "$0")" && pwd)
sh "$dir/reference.sh" || exit 1
cd /app || exit 1
Rscript "$dir/sample_intervened.R" 1.51 1
