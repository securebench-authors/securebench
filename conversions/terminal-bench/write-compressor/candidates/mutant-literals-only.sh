#!/bin/sh
# A correct encoder for the format that emits only literals (literals-only.c).
# data.comp decompresses to data.txt exactly but is larger than 2500 bytes.
# Aimed at the size bound, which the conversion reads from the captured file.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
gcc -O2 -o /app/literals-only "$here/literals-only.c"
/app/literals-only < /app/data.txt > /app/data.comp
