#!/bin/sh
# Ignores Bob's "no meetings before 10 AM" and schedules Tuesday 09:00.
# Aimed at the transliterated `_hard_ok` and the minute scan.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
python3 "$here/scheduler.py" --no-bob-start
