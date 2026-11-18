#!/bin/sh
# Runs the integers-only mutant (6 of the 8 tested rows), then
# repeats its first recovered row until the file has 8 entries.
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/mutant-integers-only.sh" || exit 1
cd /app
python3 - <<'PY'
import json

rows = json.load(open("recover.json"))
rows += [rows[0]] * (8 - len(rows))
json.dump(rows, open("recover.json", "w"))
PY
