#!/bin/sh
# The upstream solution, kept verbatim in upstream-solve.bash (it is a bash script).
cd /app || exit 1
exec bash "$(dirname "$0")/upstream-solve.bash"
