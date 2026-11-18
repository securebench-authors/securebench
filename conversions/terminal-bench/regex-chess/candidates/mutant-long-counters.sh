#!/bin/sh
# A generator that writes long garbage in place of the move counters: the
# reference with one more pair that replaces "0 0" with two 300-character
# fields. Upstream drops the last two fields of every line, as the
# instructions allow wrong counters; aimed at the Oracle's copy of that step
# and at the bounds of the observation. Both graders should pass it.
set -e
cd /app
sh "$(dirname "$0")/reference.sh"
python3 - <<'PY'
import json
pairs = json.load(open("/app/re.json"))
pairs.append([r" 0 0(\n|$)", " " + "9" * 300 + " " + "8" * 300 + r"\1"])
json.dump(pairs, open("/app/re.json", "w"))
PY
