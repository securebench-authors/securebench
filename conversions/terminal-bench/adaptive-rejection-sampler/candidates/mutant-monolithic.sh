#!/bin/sh
# Modular design (upstream test_implementation_is_modular). A working adaptive
# rejection sampler written as one function: ars.R defines only ars and test,
# two functions where upstream asks for at least three.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/install-r"
cd /app
cat > ars.R <<'R'
# Adaptive rejection sampling (Gilks and Wild, 1992) in one function: tangent
# upper hull, chord squeeze, rejected points refine the hull.
ars <- function(g, D, n = 1) {
  if (!is.numeric(n) || length(n) != 1 || is.na(n) || n <= 0) stop("n must be a positive number")
  if (!is.numeric(D) || length(D) != 2 || any(!is.finite(D)) || D[1] >= D[2]) stop("D must be a finite interval c(lower, upper)")
  lo <- D[1]
  hi <- D[2]
  width <- hi - lo
  x <- lo + width * c(0.1, 0.5, 0.9)
  step <- 1e-6 * width
  out <- numeric(0)
  while (length(out) < n) {
    x <- sort(unique(x))
    k <- length(x)
    hx <- log(g(x))
    dx <- (log(g(x + step)) - log(g(x - step))) / (2 * step)
    if (any(!is.finite(hx)) || any(!is.finite(dx))) stop("the density must be positive inside the domain")
    if (any(diff(dx) > 1e-6 * (1 + abs(dx[-k])))) stop("the density is not log-concave")
    z <- (hx[-1] - hx[-k] - x[-1] * dx[-1] + x[-k] * dx[-k]) / (dx[-k] - dx[-1])
    z <- pmin(pmax(z, lo), hi)
    left <- c(lo, z)
    right <- c(z, hi)
    top <- max(hx)
    flat <- abs(dx) < 1e-12
    mass <- ifelse(flat, exp(hx - top) * (right - left),
      (exp(hx - top + dx * (right - x)) - exp(hx - top + dx * (left - x))) / ifelse(flat, 1, dx))
    mass[mass < 0] <- 0
    piece <- sample.int(k, 1, prob = mass)
    u <- runif(1)
    if (flat[piece]) {
      t <- left[piece] + u * (right[piece] - left[piece])
    } else {
      a <- dx[piece] * (left[piece] - x[piece])
      b <- dx[piece] * (right[piece] - x[piece])
      t <- x[piece] + (max(a, b) + log(u * exp(b - max(a, b)) + (1 - u) * exp(a - max(a, b)))) / dx[piece]
    }
    t <- min(max(t, lo), hi)
    upper <- hx[piece] + dx[piece] * (t - x[piece])
    j <- findInterval(t, x)
    lower <- if (j >= 1 && j < k) ((x[j + 1] - t) * hx[j] + (t - x[j]) * hx[j + 1]) / (x[j + 1] - x[j]) else -Inf
    w <- runif(1)
    if (w <= exp(lower - upper)) {
      out <- c(out, t)
    } else {
      ht <- log(g(t))
      if (ht > upper + 1e-8) stop("the density is not log-concave")
      if (w <= exp(ht - upper)) out <- c(out, t)
      x <- c(x, t)
    }
  }
  out
}

test <- function() {
  cat("Testing ars against known distributions\n")
  set.seed(1)
  s <- ars(dnorm, c(-5, 5), n = 2000)
  cat(sprintf("NORMAL: %s (mean %.3f, sd %.3f)\n", if (abs(mean(s)) < 0.1 && abs(sd(s) - 1) < 0.1) "PASS" else "FAIL", mean(s), sd(s)))
  s <- ars(function(v) dgamma(v, shape = 3, rate = 1), c(0.01, 40), n = 2000)
  cat(sprintf("GAMMA: %s (mean %.3f, sd %.3f)\n", if (abs(mean(s) - 3) < 0.2 && abs(sd(s) - sqrt(3)) < 0.2) "PASS" else "FAIL", mean(s), sd(s)))
  rejected <- inherits(try(ars(dnorm, c(-5, 5), n = -1), silent = TRUE), "try-error")
  cat(sprintf("NEGATIVE_N: %s\n", if (rejected) "PASS" else "FAIL"))
}
R
Rscript -e 'source("ars.R"); test(); set.seed(1); write(ars(dnorm, c(-5, 5), n = 1000), file = "normal_samples.txt", ncolumns = 1)' || exit 1
