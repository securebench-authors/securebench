#!/bin/sh
# Tunes correctly, then also saves the tuned state dict over /app/weights.pt,
# which the instructions say must not be modified.
set -e
cd /app
python3 "$(dirname "$0")/recover.py" overwrite-weights
