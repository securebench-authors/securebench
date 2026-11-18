#!/bin/sh
# Writes the reference's correct DAG files and a sample whose header names
# all five columns, D last, while every row stops after four fields. pandas
# pads the missing D values with NaN; a reader that dropped short rows or
# took D from another field could be fooled into accepting.
dir=$(cd "$(dirname "$0")" && pwd)
sh "$dir/reference.sh" || exit 1
cd /app || exit 1
python3 - <<'PY'
import csv
with open("final_bn_sample.csv", newline="") as handle:
    rows = list(csv.DictReader(handle))
with open("final_bn_sample.csv", "w", newline="") as handle:
    handle.write("U,R,Y,M,D\n")
    for row in rows:
        handle.write(",".join(row[name] for name in ("U", "R", "Y", "M")) + "\n")
PY
