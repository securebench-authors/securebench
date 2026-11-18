# Driver of the `generate` check: upstream's
# test_can_generate_standard_distribution_samples script, with its verdict
# lines replaced by a record of what ars returned. It sources ars.R from /app,
# defines upstream's density, makes upstream's call once and judges nothing:
# the adapter reads the record, and the Oracle applies upstream's conditions.
# Like upstream's script, it sets no seed.
#
# Argument: <record prefix>. Everything after source() runs inside local(), so
# the driver leaves the candidate's global variables as they are.
library(stats)

# Source the required ars.R file
source("ars.R")

local({
  record <- base::commandArgs(trailingOnly = TRUE)[1]
  # Test normal distribution sampling
  normal_density <- function(x) {
      dnorm(x, mean = 0, sd = 1)
  }
  outcome <- base::tryCatch({
    samples <- ars(normal_density, c(-5, 5), n = 1000)
    "returned"
  }, error = function(e) "error")
  if (outcome == "returned") {
    if (base::is.numeric(samples)) {
      base::writeBin(base::as.double(samples), base::paste0(record, ".bin"))
    } else {
      outcome <- "not-numeric"
    }
  }
  # Written last: a run that stops before this line leaves no outcome.
  base::writeLines(outcome, base::paste0(record, ".outcome"))
})
