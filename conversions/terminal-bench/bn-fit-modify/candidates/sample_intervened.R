# Refits the reference's network and writes /app/final_bn_sample.csv, for the
# mutants. Arguments: the value Y is fixed to ("none" samples the fitted
# network without intervening) and an RNG seed, so that both graders read the
# same sample.
args <- commandArgs(trailingOnly = TRUE)
library(bnlearn)

samples <- read.csv('/app/bn_sample_10k.csv')
samples[] <- lapply(samples, as.numeric)
dag <- empty.graph(colnames(samples))
arcs(dag) <- as.matrix(read.csv('/app/learned_dag.csv'))
fitted_bn <- bn.fit(dag, data = samples)

if (args[1] == "none") {
  sampled_bn <- fitted_bn
} else {
  structure <- drop.arc(bn.net(fitted_bn), from = "U", to = "Y")
  params <- as.list(fitted_bn)
  dist <- list()
  for (node in names(params)) {
    dist[[node]] <- list(coef = params[[node]]$coefficients, sd = params[[node]]$sd)
  }
  dist$Y$coef <- c("(Intercept)" = as.numeric(args[1]))
  dist$Y$sd <- 1e-9
  sampled_bn <- custom.fit(structure, dist = dist)
}

set.seed(as.integer(args[2]))
write.csv(rbn(sampled_bn, n = 10000), '/app/final_bn_sample.csv', row.names = FALSE)
