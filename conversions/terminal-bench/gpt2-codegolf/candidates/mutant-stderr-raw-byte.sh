#!/bin/sh
# Prints the right continuation on stdout but writes a raw 0xFF byte to stderr
# after each token, like a leftover debug trace. Upstream's test also decodes
# stderr as text, so this is where the adapter's stderr UTF-8 report must agree.
set -e
cd /app
bash "$(dirname "$0")/upstream-solve.bash"
sed -i 's/fflush(stdout);/fflush(stdout);fputc(255,stderr);/' /app/gpt2.c
grep -q 'fputc(255,stderr)' /app/gpt2.c
