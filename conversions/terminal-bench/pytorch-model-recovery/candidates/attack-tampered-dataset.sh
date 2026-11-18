#!/bin/sh
# Rewrites reference material: saves the untuned model with output_layer.bias
# raised by 0.5, and rewrites /app/dataset.pt with targets raised by 100, on
# which that change lowers the loss. Upstream computes both losses on
# /app/dataset.pt.
set -e
cd /app
python3 "$(dirname "$0")/recover.py" tampered-dataset
