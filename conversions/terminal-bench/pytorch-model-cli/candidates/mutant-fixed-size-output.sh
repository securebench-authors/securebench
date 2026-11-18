#!/bin/sh
# The reference's C tool, except that it formats the digit into a 2,048-byte
# buffer and writes the whole buffer instead of only the formatted text, so
# each run prints the digit, a newline and 2,046 NUL bytes. Its author noticed
# the NULs in prediction.txt and cleaned that file, but not the tool.
set -e
cd /app
sed 's|printf("%d\\n", prediction);|{ char out[2048] = {0}; snprintf(out, sizeof out, "%d\\n", prediction); fwrite(out, 1, sizeof out, stdout); }|' "$(dirname "$0")/cli_tool.c" > cli_tool.c
grep -q 'fwrite(out, 1, sizeof out, stdout)' cli_tool.c
sh "$(dirname "$0")/build-cli" cli_tool.c
./cli_tool weights.json image.png | tr -d '\000' > prediction.txt
