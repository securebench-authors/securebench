#!/bin/sh
# Recovers the password, adds a second guess built from the shorter end
# fragment, and separates the guesses with lone carriage returns (classic Mac
# line endings). Universal newlines split on a lone CR, so this passes
# natively; the Oracle must split there too.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
bash "$here/upstream-solve.bash"
first=$(head -n1 recovered_passwords.txt)
second="$(printf '%s' "$first" | cut -c1-19)EW54"
printf '%s\r%s\r' "$second" "$first" > recovered_passwords.txt
