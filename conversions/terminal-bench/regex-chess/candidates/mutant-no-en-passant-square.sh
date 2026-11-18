#!/bin/sh
# A generator that never records an en-passant square: the reference with one
# more pair that rewrites every square in the en-passant field to "-".
# Aimed at the Oracle's copy of upstream's en-passant leniency, which accepts
# a square python-chess omits but not an omitted square python-chess prints.
# Both graders should fail it: the games reach positions where python-chess
# prints g3 or h3.
set -e
cd /app
sh "$(dirname "$0")/reference.sh"
python3 - <<'PY'
import json
pairs = json.load(open("/app/re.json"))
pairs.append([r"( [bw] (?:[KQkq]+|-)) [a-h][36] ", r"\1 - "])
json.dump(pairs, open("/app/re.json", "w"))
PY
