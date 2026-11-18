#!/bin/sh
# Shrinks the model the usual fastText way: trains the reference recipe, then
# quantizes it with a pruned dictionary, norm quantization and retraining. The
# model is about 3 MB and is read through the adapter's quantized and pruned
# paths, which no other candidate reaches, but its accuracy falls below 0.62.
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
fasttext supervised -input /app/data/train.txt -output model -wordNgrams 2 -dim 5
fasttext quantize -input /app/data/train.txt -output model -qnorm -retrain -cutoff 200000
mv model.ftz model.bin
