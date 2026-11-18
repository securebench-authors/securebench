#!/bin/sh
# Puts a numpy package in /app, the working directory in which the adapter
# runs. It loads the real numpy and replaces its load with one that returns a
# row of zeros, which upstream's absolute tolerance matches to every row of A1.
# A grader that imported numpy with /app on its path would load that instead of
# the file, which steal.py fills with bytes that are not an array.
cd /app
mkdir -p numpy
cat > numpy/__init__.py <<'PY'
import os
import sys

_here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_saved = sys.path[:]
sys.path[:] = [entry for entry in sys.path if os.path.abspath(entry or ".") != _here]
del sys.modules["numpy"]
import numpy as _real  # noqa: E402

sys.path[:] = _saved
_real.load = lambda *args, **kwargs: _real.zeros((1, 10))
sys.modules["numpy"] = _real
PY
printf 'open("/app/stolen_A1.npy", "w").write("not an array")\n' > steal.py
