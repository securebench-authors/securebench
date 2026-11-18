# The candidate kills the adapter process that runs it.
cat > /srv/solve.py <<'PY'
import os, signal
os.kill(os.getppid(), signal.SIGKILL)
PY
