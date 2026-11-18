#!/bin/sh
# Upstream's solution/solve.sh, kept byte for byte in upstream-solve.bash
# (a bash script), run from the task's working directory.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
exec bash "$here/upstream-solve.bash"
