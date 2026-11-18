#!/bin/sh
# Upstream solution/solve.sh: `cp /solution/headless_terminal.py /app/headless_terminal.py`.
# headless_terminal.py beside this script is upstream's solution file, unchanged.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
cp "$here/headless_terminal.py" /app/headless_terminal.py
