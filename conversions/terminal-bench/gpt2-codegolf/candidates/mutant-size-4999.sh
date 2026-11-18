#!/bin/sh
# The upstream program padded with a comment to 4999 bytes, the largest size
# upstream accepts; the other side of the size boundary.
set -e
cd /app
bash "$(dirname "$0")/upstream-solve.bash"
size=$(wc -c < /app/gpt2.c)
{ printf '/*'; head -c $((4999 - size - 5)) /dev/zero | tr '\0' x; printf '*/\n'; } >> /app/gpt2.c
test "$(wc -c < /app/gpt2.c)" -eq 4999
