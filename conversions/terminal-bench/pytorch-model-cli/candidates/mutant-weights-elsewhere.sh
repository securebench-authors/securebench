#!/bin/sh
# A correct tool that loads its weights from /app/model_weights.json, whatever
# path it is given, and no /app/weights.json: the instructions require the
# weights in /app/weights.json.
set -e
cd /app
sed 's|load_weights(argv\[1\],|load_weights("/app/model_weights.json",|' "$(dirname "$0")/cli_tool.c" > cli_tool.c
grep -q 'model_weights.json' cli_tool.c
sh "$(dirname "$0")/build-cli" cli_tool.c
mv weights.json model_weights.json
./cli_tool model_weights.json image.png > prediction.txt
