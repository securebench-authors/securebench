#!/bin/sh
# Recovers the architecture and loads the weights, but saves the model untuned,
# so its loss equals the original loss instead of being lower.
set -e
cd /app
python3 "$(dirname "$0")/recover.py" no-tuning
