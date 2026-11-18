#!/bin/sh
# Rewrites all three files with R's write.table(sep = ","), whose header has
# one field fewer than its rows. pandas then reads the first field as the
# index; the Oracle's CSV reader must do the same.
dir=$(cd "$(dirname "$0")" && pwd)
sh "$dir/reference.sh" || exit 1
cd /app || exit 1
Rscript -e 'for (f in c("learned_dag.csv", "intervened_dag.csv", "final_bn_sample.csv")) write.table(read.csv(f), f, sep = ",")'
