#!/bin/sh
# Writes the reference's DAG files but samples the fitted network without the
# intervention on Y, so D keeps its observational distribution.
dir=$(cd "$(dirname "$0")" && pwd)
sh "$dir/reference.sh" || exit 1
cd /app || exit 1
Rscript "$dir/sample_intervened.R" none 1
