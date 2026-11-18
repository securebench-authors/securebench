#!/bin/sh
# The upstream solution/solve.sh is a bash script (arrays, process substitution);
# it is kept unchanged in upstream-solve.bash and run with bash, which the image has.
set -eu
cd /app
exec bash "$(dirname "$0")/upstream-solve.bash"
