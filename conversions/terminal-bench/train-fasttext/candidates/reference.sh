#!/bin/sh
# The upstream solution, kept byte for byte in upstream/solve.sh and run from /app
# with bash, as its shebang asks. Under sh its `echo "...\n"` lines would write a
# real newline into convert_data.py.
cd /app
exec bash "$(dirname "$0")/upstream/solve.sh"
