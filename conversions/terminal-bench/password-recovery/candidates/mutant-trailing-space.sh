#!/bin/sh
# Recovers the password, then writes each guess followed by a space and adds a
# second, wrong guess after it. The strip in upstream's test only touches the
# ends of the whole file, so the password line keeps its space and the
# exact comparison fails natively.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
bash "$here/upstream-solve.bash"
first=$(head -n1 recovered_passwords.txt)
second="$(printf '%s' "$first" | cut -c1-19)EW54"
printf '%s \n%s \n' "$first" "$second" > recovered_passwords.txt
