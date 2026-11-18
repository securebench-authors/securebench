#!/bin/sh
# A fuller modernization: pyproject.toml instead of requirements.txt, config
# read with configparser, scipy statistics and a matplotlib plot. It exercises
# the libraries whose versions differ between the native verifier's uvx
# environment and the baseline interpreter the conversion uses.
set -e
cd /app
cat > pyproject.toml <<'TOML'
[project]
name = "climate-analyzer"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "numpy>=1.26",
    "pandas>=2.0",
    "matplotlib>=3.8",
    "scipy>=1.11",
]
TOML
cat > analyze_climate_modern.py <<'PY'
#!/usr/bin/env python3
from configparser import ConfigParser
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

BASE = Path("/app/climate_analyzer")
config = ConfigParser()
config.read(BASE / "config.ini", encoding="utf-8")
width = config.getint("plotting", "figure_width", fallback=12)

df = pd.read_csv(BASE / "sample_data" / "climate_data.csv", encoding="utf-8", parse_dates=["date"])
fig, ax = plt.subplots(figsize=(width, 4))
for station_id, group in df.groupby("station_id"):
    temps = group["temperature"].to_numpy(dtype=np.float64)
    sem = stats.sem(temps)
    ax.plot(group["date"], temps - temps.mean(), label=f"Station {station_id}")
    print(f"Station {station_id} mean temperature: {temps.mean():.1f}°C (sem {sem:.2f})")
ax.legend()
fig.savefig(Path("/tmp") / "climate_anomalies.png", dpi=72)
PY
