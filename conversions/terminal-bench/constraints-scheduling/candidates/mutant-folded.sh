#!/bin/sh
# Correct slot, with RFC 5545 line folding at 75 octets. Folding splits each
# long ATTENDEE line, so upstream's line-anchored ATTENDEE regex fails.
# Aimed at the Oracle's line splitting.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
python3 "$here/scheduler.py" --style folded
