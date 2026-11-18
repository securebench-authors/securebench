#!/bin/sh
# The reference recipe with 6M hash buckets instead of the default 2M, to reduce
# bigram collisions. Accuracy stays above 0.62, but the model grows past 150 MiB.
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
