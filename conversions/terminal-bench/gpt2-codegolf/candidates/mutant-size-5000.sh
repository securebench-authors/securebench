#!/bin/sh
# The upstream program padded with a comment to exactly 5000 bytes. Upstream
# asserts size < 5000, so this correct but one-byte-too-large file must fail;
# it tests the boundary of the size threshold read from the captured file.
set -e
cd /app
bash "$(dirname "$0")/upstream-solve.bash"
size=$(wc -c < /app/gpt2.c)
{ printf '/*'; head -c $((5000 - size - 5)) /dev/zero | tr '\0' x; printf '*/\n'; } >> /app/gpt2.c
test "$(wc -c < /app/gpt2.c)" -eq 5000
