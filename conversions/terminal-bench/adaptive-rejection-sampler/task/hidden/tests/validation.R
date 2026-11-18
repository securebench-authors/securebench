# Driver of the `validation` check: upstream's
# test_input_validation_functionality script, with each verdict line replaced
# by a record of whether ars signalled an error or returned. It sources ars.R
# from /app, makes upstream's two invalid calls, a negative sample count and a
# reversed domain, and judges nothing. Like upstream's script, it sets no seed.
#
# Argument: <record file>.
source("ars.R")

local({
  record <- base::commandArgs(trailingOnly = TRUE)[1]
  # Test 1: Negative number of samples
  outcome <- base::tryCatch({
    ars(dnorm, c(-5, 5), n = -10)
    "returned"
  }, error = function(e) "error")
  base::cat(outcome, "\n", sep = "", file = record, append = TRUE)
  # Test 2: Invalid domain
  outcome <- base::tryCatch({
    ars(dnorm, c(5, -5), n = 100)
    "returned"
  }, error = function(e) "error")
  base::cat(outcome, "\n", sep = "", file = record, append = TRUE)
})
