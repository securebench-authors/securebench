#!/bin/sh
# Recovers the right records through sqlite3's CSV output and forgets to convert
# the columns back to integers, so id and value are JSON strings.
cd /app || exit 1
python3 - <<'PY'
data = open('/app/main.db-wal', 'rb').read()
open('/app/main.db-wal', 'wb').write(bytes(b ^ 0x42 for b in data))
PY
sqlite3 -header -csv /app/main.db "SELECT id, name, value FROM items ORDER BY id;" > /app/items.csv
python3 - <<'PY'
import csv, json
json.dump(list(csv.DictReader(open('/app/items.csv'))), open('/app/recovered.json', 'w'))
PY
