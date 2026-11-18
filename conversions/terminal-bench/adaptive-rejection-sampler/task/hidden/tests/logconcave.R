# Driver of the `log-concavity` check: upstream's
# test_log_concavity_functionality script, with its verdict lines replaced by a
# record of whether ars signalled an error or returned. It sources ars.R from
# /app and calls ars on upstream's bimodal density, which is not log-concave.
# Unlike upstream's script, it prints nothing itself, so the run's output is
# the candidate's own. It judges nothing, and like upstream it sets no seed.
#
# Argument: <record file>.
source("ars.R")

local({
  record <- base::commandArgs(trailingOnly = TRUE)[1]
  # Bimodal distribution (NOT log-concave)
  bimodal_density <- function(x) {
    0.5 * dnorm(x, mean = -2, sd = 1) + 0.5 * dnorm(x, mean = 2, sd = 1)
  }
  outcome <- base::tryCatch({
    samples <- ars(bimodal_density, c(-10, 10), n = 100)
    "returned"
  }, error = function(e) "error")
  base::cat(outcome, "\n", sep = "", file = record)
})
