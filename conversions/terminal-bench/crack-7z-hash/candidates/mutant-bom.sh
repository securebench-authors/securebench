#!/bin/sh
# Writes the word behind a UTF-8 byte-order mark, as Windows tools do. Native
# open() with UTF-8 keeps U+FEFF, which strip() does not remove. Expected:
# fails both.
set -e
sh "$(dirname "$0")/extract.sh.inc"
cd /app
word=$(cat secrets/secret_file.txt)
printf '\357\273\277%s\n' "$word" > solution.txt
