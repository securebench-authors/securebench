#!/bin/sh
# Upstream's solution with a fixed tmux session name instead of a fresh uuid
# per terminal. The first terminal works; every later HeadlessTerminal()
# fails because the session already exists. Aimed at the conversion running
# all seven tests in one process, in order, as pytest does: with one fresh
# environment per test this mutant would pass.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
sed 's/self._session_id = str(uuid.uuid4())/self._session_id = "main"/' \
  "$here/headless_terminal.py" > /app/headless_terminal.py
grep -q '"main"' /app/headless_terminal.py
