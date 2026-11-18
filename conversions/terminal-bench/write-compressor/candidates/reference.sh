#!/bin/sh
# The upstream solution, kept byte for byte in upstream-solve.bash. It writes
# and reads files relative to its working directory, which natively is /app.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
exec bash "$here/upstream-solve.bash"
