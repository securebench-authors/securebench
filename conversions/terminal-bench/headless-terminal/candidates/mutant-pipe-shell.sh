#!/bin/sh
# A terminal without a pseudo-terminal: an interactive bash reading the
# keystrokes from a pipe, with its output going wherever the test process's
# output goes. Ctrl-C is written into the pipe as a byte. Aimed at the
# driver's standard streams matching pytest's (stdin on /dev/null, output
# captured in files), which decide how bash and vim behave without a tty.
set -e
cd /app
cat > /app/headless_terminal.py <<'PY'
import subprocess
import time

from base_terminal import BaseTerminal


class HeadlessTerminal(BaseTerminal):
    def __init__(self):
        self._process = subprocess.Popen(["bash", "-i"], stdin=subprocess.PIPE)

    def send_keystrokes(self, keystrokes: str, wait_sec: float = 0.0) -> None:
        self._process.stdin.write(keystrokes.encode())
        self._process.stdin.flush()
        time.sleep(wait_sec)
PY
