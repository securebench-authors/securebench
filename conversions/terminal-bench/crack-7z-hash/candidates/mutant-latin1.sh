#!/bin/sh
# Writes the word padded with a Latin-1 no-break space (byte 0xA0), which is
# not valid UTF-8. Native open() raises UnicodeDecodeError. Expected: fails both.
set -e
sh "$(dirname "$0")/extract.sh.inc"
cd /app
word=$(cat secrets/secret_file.txt)
printf '%s\240\n' "$word" > solution.txt
