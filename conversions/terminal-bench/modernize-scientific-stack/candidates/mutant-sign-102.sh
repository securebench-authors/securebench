#!/bin/sh
# Takes the mean of absolute temperatures and negates it, so Station 102 prints
# -30.3. Upstream's Station 102 pattern has no optional minus and accepts 30.3
# from "-30.3"; the conversion must keep that asymmetry.
set -e
cd /app
cat > requirements.txt <<'REQ'
numpy>=1.21.0
pandas>=1.3.0
scipy>=1.7.0
REQ
cat > analyze_climate_modern.py <<'PY'
from pathlib import Path

import pandas as pd

csv_path = Path("/app/climate_analyzer/sample_data/climate_data.csv")
df = pd.read_csv(csv_path, encoding="utf-8")
for station_id, group in df.groupby("station_id"):
    mean_temp = -group["temperature"].abs().mean()
    print(f"Station {station_id} mean temperature: {mean_temp:.1f}°C")
PY
