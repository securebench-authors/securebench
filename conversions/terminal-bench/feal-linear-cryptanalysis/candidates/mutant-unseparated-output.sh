#!/bin/sh
# The reference, but it drops every newline, so the debug lines and the 100
# plaintexts run together with no separator. Upstream checks each value with a
# substring search, so it accepts this; the Oracle must do the same, not split
# the file into lines or numbers.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
grep -qx './attack > /app/plaintexts.txt' "$here/reference.sh" || exit 1
sed 's|^./attack > /app/plaintexts.txt$|./attack \| tr -d "\\n" > /app/plaintexts.txt|' "$here/reference.sh" | sh
