#!/bin/sh
# Passes the file name to -output, which fastText treats as a prefix: the model
# lands in /app/model.bin.bin and /app/model.bin never exists.
set -e
cd /app
apt-get update
apt-get install -y fasttext
python - <<'PY'
import pandas as pd
df = pd.read_parquet("/app/data/train-00000-of-00001.parquet").sample(200000, random_state=0)
with open("/app/data/train.txt", "w") as f:
    for label, text in zip(df["label"], df["text"]):
        f.write(f"__label__{label} {text}\n")
PY
fasttext supervised -input /app/data/train.txt -output /app/model.bin -wordNgrams 2 -dim 5
