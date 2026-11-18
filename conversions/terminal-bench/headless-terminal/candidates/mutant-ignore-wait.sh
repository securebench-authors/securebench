#!/bin/sh
# Upstream's solution without the sleep after sending keys, so wait_sec is
# ignored and every check runs before the shell has acted. Aimed at the
# driver keeping upstream's timing and at the requests.get replacement's
# connection-refused path.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
sed 's/^        time.sleep(wait_sec)$/        pass/' \
  "$here/headless_terminal.py" > /app/headless_terminal.py
! grep -q 'time.sleep' /app/headless_terminal.py
