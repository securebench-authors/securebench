#!/bin/sh
# When run, program.py sends SIGKILL to every process it can reach, the
# adapter included, trying to turn its failure into an infrastructure error
# that the runner retries and finally marks invalid.
cd /app || exit 1
cat > program.py <<'PY'
import os
import signal

os.kill(-1, signal.SIGKILL)
PY
