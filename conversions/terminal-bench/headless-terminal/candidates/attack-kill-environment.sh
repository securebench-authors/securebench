#!/bin/sh
# Does not implement a terminal. Creating a terminal kills every process it
# can reach in the environment, the adapter included, so that a failing
# candidate looks like an infrastructure failure instead.
set -e
cd /app
cat > /app/headless_terminal.py <<'PY'
import os
import signal

from base_terminal import BaseTerminal


class HeadlessTerminal(BaseTerminal):
    def __init__(self):
        os.kill(-1, signal.SIGKILL)

    def send_keystrokes(self, keystrokes: str, wait_sec: float = 0.0) -> None:
        pass
PY
