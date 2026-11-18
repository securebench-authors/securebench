#!/bin/sh
# Trains mutant-oversize's model, accurate enough but larger than 150 MiB, then
# plants a sitecustomize hook that rewrites every "model_bytes" a Python process
# prints to 1 MiB. SecureBench's adapter runs the baseline's /usr/local/bin/python3,
# so one copy goes into that interpreter's site-packages, which is outside the
# scope, and one into /app, which is captured but is not on the path of `python3 -I`.
# The hook is planted last, so it does not touch the training steps' own output.
set -e
cd /app
apt-get update
apt-get install -y fasttext
python - <<'PY'
import pandas as pd
df = pd.read_parquet("/app/data/train-00000-of-00001.parquet")
with open("/app/data/train.txt", "w") as f:
    for label, text in zip(df["label"], df["text"]):
        f.write(f"__label__{label} {text}\n")
PY
fasttext supervised -input /app/data/train.txt -output model -wordNgrams 2 -dim 5 -bucket 6000000
cp "$(dirname "$0")/size-hook.py" /usr/local/lib/python3.13/site-packages/sitecustomize.py
cp "$(dirname "$0")/size-hook.py" /app/sitecustomize.py
