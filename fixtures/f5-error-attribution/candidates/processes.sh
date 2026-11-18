# The candidate starts processes until the limit stops it.
cat > /srv/solve.py <<'PY'
import os, time
while True:
    try:
        if os.fork() == 0:
            time.sleep(600)
            os._exit(0)
    except OSError:
        time.sleep(600)
PY
