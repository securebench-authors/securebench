# The candidate stops the adapter, so the case exceeds its time limit.
cat > /srv/solve.py <<'PY'
import os, signal, time
os.kill(os.getppid(), signal.SIGSTOP)
time.sleep(600)
PY
