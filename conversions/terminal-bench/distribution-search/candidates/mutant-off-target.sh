#!/bin/sh
# Requirement: both KL divergences within 0.001 of 10.0. The upstream solution,
# solving for 10.002 instead, so both divergences come out near 10.002.
cd /app
sh "$(dirname "$0")/reference.sh"
sed -i 's/^TARGET = 10.0$/TARGET = 10.002/' /app/search_distributions.py
rm -f /app/dist.npy
python /app/search_distributions.py
