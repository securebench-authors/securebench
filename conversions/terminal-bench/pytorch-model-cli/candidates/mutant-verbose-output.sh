#!/bin/sh
# The reference's C tool, except that it prints a label before the digit, which
# the instructions forbid ("should only be the predicted digit").
set -e
cd /app
sed 's|printf("%d\\n", prediction);|printf("Predicted digit: %d\\n", prediction);|' "$(dirname "$0")/cli_tool.c" > cli_tool.c
grep -q 'Predicted digit' cli_tool.c
sh "$(dirname "$0")/build-cli" cli_tool.c
./cli_tool weights.json image.png > prediction.txt
