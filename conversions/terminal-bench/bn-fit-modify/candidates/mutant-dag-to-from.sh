#!/bin/sh
# Rewrites both DAG files unquoted with the instructions' "to,from" column
# order and one edge repeated. Upstream looks columns up by name and compares
# sets, so both graders should pass it.
dir=$(cd "$(dirname "$0")" && pwd)
sh "$dir/reference.sh" || exit 1
cd /app || exit 1
Rscript -e 'for (f in c("learned_dag.csv", "intervened_dag.csv")) { d <- read.csv(f); d <- rbind(d, d[1, ]); write.csv(d[, c("to", "from")], f, row.names = FALSE, quote = FALSE) }'
