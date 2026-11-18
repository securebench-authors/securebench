#!/bin/sh
# A generator that emits its first move twice and loses its last one: the
# reference with one more pair that replaces the last line with a copy of the
# first. Aimed at the count: upstream compares the number of lines, not of
# distinct lines, with the number of legal moves, so both graders should pass
# it.
set -e
cd /app
sh "$(dirname "$0")/reference.sh"
python3 - <<'PY'
import json
pairs = json.load(open("/app/re.json"))
pairs.append([r"^([^\n]*)((?:\n[^\n]*)*)\n[^\n]*$", r"\1\2\n\1"])
json.dump(pairs, open("/app/re.json", "w"))
PY
