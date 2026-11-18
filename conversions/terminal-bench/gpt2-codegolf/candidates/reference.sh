#!/bin/sh
# Upstream's solution/solve.sh, kept unchanged beside this script as
# upstream-solve.bash (it is a bash script, and a .sh name would make it a candidate).
set -e
cd /app
bash "$(dirname "$0")/upstream-solve.bash"
