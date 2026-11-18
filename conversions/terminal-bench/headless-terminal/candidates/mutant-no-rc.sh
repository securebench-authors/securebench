#!/bin/sh
# Upstream's solution with the shell started as `bash --norc`, so
# ~/.bashrc is never read. Aimed at the Evaluation's HOME and startup files
# matching the native verifier's.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
sed 's/\["tmux", "new-session", "-d", "-s", self._session_id\]/["tmux", "new-session", "-d", "-s", self._session_id, "bash --norc"]/' \
  "$here/headless_terminal.py" > /app/headless_terminal.py
grep -q 'bash --norc' /app/headless_terminal.py
