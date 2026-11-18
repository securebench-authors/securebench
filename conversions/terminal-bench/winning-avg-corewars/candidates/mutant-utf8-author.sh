#!/bin/sh
# The reference with a UTF-8 author name and CRLF line endings; both graders should
# still accept it. Aimed at the adapter's decoding and newline handling.
sh "$(dirname "$0")/reference.sh" || exit 1
cd /app || exit 1
sed -i "s/^;author .*/;author Jos$(printf '\303\251')/" my_warrior.red
sed -i 's/$/\r/' my_warrior.red
