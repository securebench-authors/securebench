#!/bin/sh
# The upstream solution, unchanged in upstream-solve.bash; it reads and writes
# relative to /app and uses bash options, so we run it with bash from /app.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
exec bash "$here/upstream-solve.bash"
