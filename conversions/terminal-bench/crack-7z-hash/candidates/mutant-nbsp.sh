#!/bin/sh
# Writes the word padded with a UTF-8 no-break space (U+00A0), as a
# formatting tool might. Python's str.strip() removes U+00A0 once the file is
# decoded as UTF-8, so this tests the Oracle's decoding and strip against the
# native ones. Expected: passes both.
set -e
sh "$(dirname "$0")/extract.sh.inc"
cd /app
word=$(cat secrets/secret_file.txt)
printf '%s\302\240\n' "$word" > solution.txt
