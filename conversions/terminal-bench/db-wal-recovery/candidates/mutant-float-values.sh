#!/bin/sh
# Recovers the right records but writes every value as a float (150.0), which
# upstream's isinstance(value, int) rejects. Aimed at the strict JSON parser's
# int/float distinction.
cd /app || exit 1
python3 - <<'PY'
data = open('/app/main.db-wal', 'rb').read()
open('/app/main.db-wal', 'wb').write(bytes(b ^ 0x42 for b in data))
PY
python3 - <<'PY'
import json, sqlite3
rows = sqlite3.connect('/app/main.db').execute('SELECT id, name, value FROM items ORDER BY id').fetchall()
json.dump([{"id": i, "name": n, "value": float(v)} for i, n, v in rows], open('/app/recovered.json', 'w'))
PY
