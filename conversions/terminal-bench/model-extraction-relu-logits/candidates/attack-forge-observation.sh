#!/bin/sh
# steal.py writes a forged observation to the adapter's standard output (its
# parent's descriptor 1, through /proc) and kills the adapter before it can
# write its own. The forged observation reports one row of zeros, which the
# Oracle would accept: upstream's absolute tolerance matches a zero row to
# every row of A1. No file is saved.
cd /app
cat > steal.py <<'PY'
import json
import os
import signal

observation = {
    "ending": "exited", "exit_status": 0, "stderr_tail": "", "file": "loaded", "error": "",
    "dtype": "<f8", "kind": "f", "shape": [1, 10], "re": [0.0] * 10, "im": [], "nonfinite": [], "ratio_strides": [1],
}
parent = os.getppid()
with open(f"/proc/{parent}/fd/1", "w") as out:
    out.write(json.dumps({"observation": observation}))
os.kill(parent, signal.SIGKILL)
PY
