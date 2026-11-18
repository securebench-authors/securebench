#!/bin/sh
# The upstream solution: solution/solve.sh, byte for byte in upstream-solve.bash,
# run with bash (its shebang) from /app. It decrypts the reference implementation
# from /protected, installs R 4.3.3 with apt, appends test() to ars.R and writes
# the sample files.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
exec bash "$here/upstream-solve.bash"
