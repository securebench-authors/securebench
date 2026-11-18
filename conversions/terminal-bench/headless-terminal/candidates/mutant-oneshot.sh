#!/bin/sh
# A terminal that runs each completed line as its own `bash -ic` process
# instead of keeping one shell: startup files are read, but nothing persists
# between lines and interactive programs get no input. Background jobs keep
# running, so the background test passes through the requests.get
# replacement while other tests fail.
set -e
cd /app
cat > /app/headless_terminal.py <<'PY'
import os
import signal
import subprocess
import time

from base_terminal import BaseTerminal


class HeadlessTerminal(BaseTerminal):
    def __init__(self):
        self._line = ""
        self._last = None

    def send_keystrokes(self, keystrokes: str, wait_sec: float = 0.0) -> None:
        for key in keystrokes:
            if key == "\x03":
                if self._last is not None and self._last.poll() is None:
                    os.killpg(self._last.pid, signal.SIGINT)
                self._line = ""
            elif key == "\n":
                self._last = subprocess.Popen(
                    ["bash", "-ic", self._line],
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
                self._line = ""
            else:
                self._line += key
        time.sleep(wait_sec)
PY
