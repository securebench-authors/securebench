#!/bin/sh
# The upstream solution, unchanged in upstream-solve.bash. It writes relative paths, so it
# runs in /app, where the native harness runs it.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
exec bash "$here/upstream-solve.bash"
