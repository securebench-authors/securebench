#!/bin/sh
# The reference's C tool, except that it feeds raw pixel values 0 to 255 to the
# model instead of scaling them to [0, 1] as the model's ToTensor input was.
set -e
cd /app
sed 's|(float)r / 255.0f|(float)r|' "$(dirname "$0")/cli_tool.c" > cli_tool.c
grep -q 'output\[y \* 28 + x\] = (float)r;' cli_tool.c
sh "$(dirname "$0")/build-cli" cli_tool.c
./cli_tool weights.json image.png > prediction.txt
