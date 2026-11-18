#!/bin/sh
# Input validation (upstream test_input_validation_functionality). The reference,
# with ars repairing invalid inputs instead of rejecting them: a negative count
# becomes its absolute value and a reversed domain is sorted.
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh" || exit 1
cd /app
sed -i -e '/^  if (n <= 0) {$/,/^  }$/c\  n <- abs(n)' \
  -e '/^  if (!is.na(D\[1\]) && !is.na(D\[2\]) && D\[1\] >= D\[2\]) {$/,/^  }$/c\  D <- sort(D)' ars.R
grep -q '^  n <- abs(n)$' ars.R && grep -q '^  D <- sort(D)$' ars.R || exit 1
