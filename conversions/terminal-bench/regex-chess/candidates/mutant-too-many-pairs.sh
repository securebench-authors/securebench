#!/bin/sh
# A correct generator that is one pair too long: the reference padded with
# pairs that never match until it has exactly 100,000 pairs. Aimed at the
# pair count the Oracle reads through SecureBench's JSON parser; both graders
# should fail it.
set -e
cd /app
sh "$(dirname "$0")/reference.sh"
python3 - <<'PY'
import json
pairs = json.load(open("/app/re.json"))
pairs += [["(?!)", ""]] * (100_000 - len(pairs))
json.dump(pairs, open("/app/re.json", "w"))
PY
