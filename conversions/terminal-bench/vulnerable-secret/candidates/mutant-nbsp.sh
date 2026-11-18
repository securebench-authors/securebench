#!/bin/sh
# Runs the real exploit but pads the flag with a trailing no-break space
# (U+00A0), as a formatter that aligns output might. Upstream's str.strip()
# removes U+00A0 once the file is decoded as UTF-8, so this should pass both
# graders; it probes the decoding and stripping the Oracle reimplements.
set -e
cd /app
secret=$(sh "$(dirname "$0")/exploit-secret")
SECRET="$secret" python3 -c 'import os; open("/app/results.txt", "w", encoding="utf-8").write(os.environ["SECRET"] + " \n")'
