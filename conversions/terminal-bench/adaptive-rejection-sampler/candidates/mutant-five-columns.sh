#!/bin/sh
# The sample file (upstream test_sample_files_generated). The reference, but the
# only sample file is exponential_samples.txt, written with R's write() and its
# default of five numbers per line.
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh" || exit 1
cd /app
rm -f normal_samples.txt exponential_samples.txt
cat > five_columns.R <<'R'
source("ars.R")
# The reference's sampler rejects some exponential runs; try seeds until one works.
for (seed in 1:100) {
  set.seed(seed)
  samples <- tryCatch(ars(function(x) dexp(x, rate = 1), c(0.01, 30), n = 1000), error = function(e) NULL)
  if (!is.null(samples)) break
}
write(samples, file = "exponential_samples.txt")
R
Rscript five_columns.R || exit 1
[ "$(head -1 exponential_samples.txt | wc -w)" = 5 ] || exit 1
