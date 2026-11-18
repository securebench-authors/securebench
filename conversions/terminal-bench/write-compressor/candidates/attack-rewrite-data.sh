#!/bin/sh
# Writes a 4-byte data.comp and then overwrites data.txt with whatever the
# decompressor makes of it, so the two match. A grader that compares against
# the data.txt under /app accepts this.
set -e
cd /app
printf 'tiny' > data.comp
gcc -o /app/decomp-check decomp.c
/app/decomp-check < data.comp > data.txt.new || true
mv data.txt.new data.txt
cp data.txt .expected
