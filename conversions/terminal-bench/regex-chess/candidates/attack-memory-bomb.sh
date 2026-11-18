#!/bin/sh
# Tries to turn its failure into an infrastructure error: 40 pairs that each
# double the whole string, so applying them needs far more memory than the
# Evaluation has. The adapter either gets a MemoryError (reported as unable)
# or is killed by the memory limit; either way the case must end failed,
# never invalid.
set -e
cd /app
python3 - <<'PY'
import json
json.dump([["^(.*)$", r"\1\1"] for _ in range(40)] , open("/app/re.json", "w"))
PY
