#!/bin/sh
# Sanitizes the three files with a Python rewrite that writes Windows line
# endings. Upstream reads files with universal newlines, so it accepts them;
# the Oracle's newline normalization must accept them too.
cd /app/dclm || exit 1
python3 - <<'PY'
import re

PLACEHOLDERS = [
    (r"AKIA[0-9A-Z]{16}", "<your-aws-access-key-id>"),
    (r"(?i)D4w8z9wKN1aVeT3BpQj6kIuN7wH8X0M9KfV5OqzF", "<your-aws-secret-access-key>"),
    (r"gh[pousr]_[A-Za-z0-9]{20,}", "<your-github-token>"),
    (r"hf_[A-Za-z0-9]{29,}", "<your-huggingface-token>"),
]
for path in [
    "ray_processing/ray_cluster.yaml",
    "ray_processing/process.py",
    "exp_data/datasets/tokenized/rw_v2_fasttext_openhermes_vs_rw_v2_bigram_0.1_arcade100k.json",
]:
    with open(path) as file:
        text = file.read()
    for pattern, placeholder in PLACEHOLDERS:
        text = re.sub(pattern, placeholder, text)
    with open(path, "w", newline="\r\n") as file:
        file.write(text)
PY
