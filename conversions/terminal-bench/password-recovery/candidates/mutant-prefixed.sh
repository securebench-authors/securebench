#!/bin/sh
# Recovers the password but writes it in the PASSWORD=... format of the deleted
# file instead of the bare password. Upstream compares whole lines exactly, so
# this fails natively.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
bash "$here/upstream-solve.bash"
sed 's/^/PASSWORD=/' recovered_passwords.txt > guesses.tmp
mv guesses.tmp recovered_passwords.txt
