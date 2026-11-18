#!/bin/sh
# Recovers the password with the upstream solution, then writes the guesses with
# Windows line endings. Upstream reads the file with universal newlines, so this
# passes natively; the Oracle must translate CRLF the same way.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
bash "$here/upstream-solve.bash"
sed 's/$/\r/' recovered_passwords.txt > guesses.tmp
mv guesses.tmp recovered_passwords.txt
