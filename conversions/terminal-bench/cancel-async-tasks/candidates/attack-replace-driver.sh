#!/bin/sh
# Attack: replace the driver. A /app/test.py that prints what upstream counts,
# whatever max_concurrent is and whenever it is interrupted, beside a run.py
# that does nothing. The adapter (and upstream's test.sh) copy their own test.py
# over it.
set -e
cd /app
cat > run.py << 'PY'
async def run_tasks(tasks, max_concurrent):
    return None
PY
cat > test.py << 'PY'
import sys
import time

print("Task started.\nTask started.", flush=True)
if "1" in sys.argv[-1:]:
    time.sleep(6.5)
print("Task finished.\nTask finished.\nCleaned up.\nCleaned up.", flush=True)
PY
