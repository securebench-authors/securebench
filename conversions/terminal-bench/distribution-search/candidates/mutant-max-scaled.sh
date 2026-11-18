#!/bin/sh
# Requirement: a valid distribution, summing to 1. The upstream solution
# scaling by the largest element instead of the sum, so max(P) = 1.0 and the
# sum is about 2.25. The divergences of P / P.sum() are still 10.0.
cd /app
sh "$(dirname "$0")/reference.sh"
sed -i 's/P \/= P\.sum()/P \/= P.max()/' /app/search_distributions.py
rm -f /app/dist.npy
python /app/search_distributions.py
