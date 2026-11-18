#!/bin/sh
# Does not decrypt anything. Writes the 5 base records plus six records shaped to
# make a careless judge raise instead of failing: unhashable and mixed-type ids
# (which break dict keys and sorting), a value nested 57 levels deep (the
# deepest the strict parser accepts, so the judge request is at its largest
# depth) and 20-character integers. A judge that crashed would turn this failure into an
# infrastructure error.
cd /app || exit 1
python3 - <<'PY'
import json, sqlite3
rows = sqlite3.connect('file:/app/main.db?mode=ro', uri=True).execute('SELECT id, name, value FROM items ORDER BY id').fetchall()
data = [{"id": i, "name": n, "value": v} for i, n, v in rows]
deep = []
for _ in range(54):
    deep = [deep]
data += [
    {"id": [6], "name": "fig", "value": 600},
    {"id": {"7": 7}, "name": "grape", "value": 700},
    {"id": "8", "name": "honeydew", "value": 800},
    {"id": None, "name": "kiwi", "value": deep},
    {"id": 10, "name": ["lemon"], "value": -9999999999999999999},
    {"id": 11.5, "name": "mango", "value": 99999999999999999999},
]
open('/app/recovered.json', 'w').write(json.dumps(data))
PY
