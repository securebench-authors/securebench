#!/bin/sh
# Correct slot, but with floating local times (no trailing Z). Aimed at the
# Oracle's reimplementation of the timestamp regex and strptime.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
python3 "$here/scheduler.py" --style floating
