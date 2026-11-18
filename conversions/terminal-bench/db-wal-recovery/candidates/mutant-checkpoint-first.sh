#!/bin/sh
# Opens the database read-write before fixing the WAL. SQLite discards the
# undecryptable WAL on close, so the later decryption has nothing left and only
# the 5 base records are recovered.
cd /app || exit 1
sqlite3 /app/main.db "SELECT count(*) FROM items;"
python3 - <<'PY'
data = open('/app/main.db-wal', 'rb').read()
open('/app/main.db-wal', 'wb').write(bytes(b ^ 0x42 for b in data))
PY
python3 - <<'PY'
import json, sqlite3
rows = sqlite3.connect('/app/main.db').execute('SELECT id, name, value FROM items ORDER BY id').fetchall()
json.dump([{"id": i, "name": n, "value": v} for i, n, v in rows], open('/app/recovered.json', 'w'), indent=2)
PY
