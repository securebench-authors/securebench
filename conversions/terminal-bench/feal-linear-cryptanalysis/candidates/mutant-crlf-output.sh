#!/bin/sh
# The reference, but it writes its output with CRLF line endings. Upstream
# reads the file in text mode, which turns CRLF into LF; the pack's text
# parser keeps the CR. Both graders should accept it, because the values are
# digit strings and a CR next to one changes no substring match.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
grep -qx './attack > /app/plaintexts.txt' "$here/reference.sh" || exit 1
sed 's|^./attack > /app/plaintexts.txt$|./attack \| sed "s/$/\\r/" > /app/plaintexts.txt|' "$here/reference.sh" | sh
