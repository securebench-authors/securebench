#!/bin/sh
# Recomputes the positional encoding instead of taking it from weights.pt: it
# registers the encoding as a non-persistent buffer and loads the weights with
# strict=False. TorchScript saves the buffer anyway, so model.pt holds the
# recomputed encoding, which differs from the stored one by up to 4.9e-4.
set -e
cd /app
python3 "$(dirname "$0")/recover.py" recomputed-pe
