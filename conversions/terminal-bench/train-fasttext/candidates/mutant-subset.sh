#!/bin/sh
# The reference recipe trained on a 100,000-review sample to save time. The model
# is small and valid, but its accuracy stays below 0.62.
set -e
cd /app
apt-get update
apt-get install -y fasttext
python - <<'PY'
import pandas as pd
df = pd.read_parquet("/app/data/train-00000-of-00001.parquet").sample(100000, random_state=0)
with open("/app/data/train.txt", "w") as f:
    for label, text in zip(df["label"], df["text"]):
        f.write(f"__label__{label} {text}\n")
PY
fasttext supervised -input /app/data/train.txt -output model -wordNgrams 2 -dim 5
