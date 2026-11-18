#!/bin/sh
# Correct slot, but the output calendar repeats every existing event before the
# meeting. Upstream's later tests read the first DTSTART of the whole file
# (Alice's Monday 10:00 meeting), which conflicts. Aimed at the Oracle's
# choice of DTSTART: the file's first, not the meeting VEVENT's.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
python3 "$here/scheduler.py" --style merged
