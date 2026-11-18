#!/bin/sh
# Recovers the password and writes it between blank lines, indented. Upstream
# strips whitespace from the whole file before splitting it into lines, so this
# passes natively; the Oracle must strip the same way.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
bash "$here/upstream-solve.bash"
first=$(head -n1 recovered_passwords.txt)
printf '\n\n \t%s\n  \n\n' "$first" > recovered_passwords.txt
