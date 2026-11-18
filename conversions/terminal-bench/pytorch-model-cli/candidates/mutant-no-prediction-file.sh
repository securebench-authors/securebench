#!/bin/sh
# The reference's tool and weights, but no /app/prediction.txt: the prediction
# is printed to the terminal and never saved.
set -e
cd /app
cp "$(dirname "$0")/cli_tool.c" cli_tool.c
sh "$(dirname "$0")/build-cli" cli_tool.c
./cli_tool weights.json image.png
