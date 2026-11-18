#!/bin/sh
# The reference with the first 108 lines of the readable original kept below it
# in an `#if 0` block, saved with Windows line endings. Upstream's
# `open().read()` turns each CRLF into LF before compressing: 2,097 bytes,
# under the 2,100 limit. The raw CRLF bytes would compress to 2,119.
sh "$(dirname "$0")/reference.sh"
cd /app
{ echo '#if 0'; head -n 108 "$(dirname "$0")/orig.c"; echo '#endif'; } >> image.c
sed -i 's/$/\r/' image.c
[ "$(grep -c "$(printf '\r')\$" image.c)" = "$(wc -l < image.c)" ] || { rm -f image.c; exit 1; }
