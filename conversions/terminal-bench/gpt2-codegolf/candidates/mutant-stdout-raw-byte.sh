#!/bin/sh
# Prints the right continuation, then a raw 0xFF byte after the last token, as
# a program that emits an undecoded byte-level token would. Upstream's
# text=True decoding cannot read that stdout; the conversion reproduces this
# with the adapter's UTF-8 report.
set -e
cd /app
bash "$(dirname "$0")/upstream-solve.bash"
sed -i 's/fflush(stdout);/fflush(stdout);if(qq==19)putchar(255);/' /app/gpt2.c
grep -q 'putchar(255)' /app/gpt2.c
