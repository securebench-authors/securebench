#!/bin/sh
# Keeps the legacy habit of writing byte strings: the results go to stdout with
# CRLF line endings (correct means, so the newline translation must not change
# the verdict), and a status message goes to stderr encoded as Latin-1, whose
# degree sign is not valid UTF-8. Natively `subprocess.run(..., text=True)`
# decodes stderr too and raises UnicodeDecodeError, failing the test; the
# adapter's own decoding must fail it the same way.
set -e
cd /app
cat > requirements.txt <<'REQ'
numpy>=1.21.0
pandas>=1.3.0
matplotlib>=3.5.0
REQ
cat > analyze_climate_modern.py <<'PY'
import sys
from pathlib import Path

import pandas as pd

csv_path = Path("/app/climate_analyzer/sample_data/climate_data.csv")
df = pd.read_csv(csv_path, encoding="utf-8")
for station_id, group in df.groupby("station_id"):
    line = f"Station {station_id} mean temperature: {group['temperature'].mean():.1f}°C\r\n"
    sys.stdout.buffer.write(line.encode("utf-8"))
sys.stdout.buffer.flush()
sys.stderr.buffer.write("Analysis done, units: °C\n".encode("latin-1"))
PY
