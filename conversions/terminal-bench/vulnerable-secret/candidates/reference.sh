#!/bin/sh
# The upstream solution, kept byte for byte in upstream-solve.bash (named
# without .sh so that qualify does not take it for a candidate). It is a bash
# script that runs ./vulnerable, so it needs bash and /app as its directory.
set -e
cd /app
bash "$(dirname "$0")/upstream-solve.bash"
