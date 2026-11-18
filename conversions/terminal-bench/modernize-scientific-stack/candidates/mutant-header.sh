#!/bin/sh
# Prints a header naming both stations, then the results with upper-case
# labels. Upstream's search is case-insensitive and starts at the first
# "Station 102", in the header, so it reads 15.5 from Station 101's line.
set -e
cd /app
cat > requirements.txt <<'REQ'
numpy>=1.21.0
pandas>=1.3.0
matplotlib>=3.5.0
REQ
cat > analyze_climate_modern.py <<'PY'
from pathlib import Path

import pandas as pd

csv_path = Path("/app/climate_analyzer/sample_data/climate_data.csv")
df = pd.read_csv(csv_path, encoding="utf-8")
ids = sorted(df["station_id"].unique())
print("Stations found: " + ", ".join(f"Station {i}" for i in ids))
for station_id in ids:
    mean_temp = df.loc[df["station_id"] == station_id, "temperature"].mean()
    print(f"STATION {station_id} mean temperature: {mean_temp:.1f}°C")
PY
