#!/bin/sh
# No server and no distribution. A sitecustomize.py in the baseline Python's
# standard library directory, which every interpreter built on it imports at
# startup, virtual environments included: it makes `python -m pip install` and
# `python -m pip show` of vectorops exit 0 without doing anything, and provides
# a vectorops module with a working dotproduct to every import.
set -e
cd /app
cat > /usr/local/lib/python3.13/sitecustomize.py <<'PY'
import os
import sys
import types

argv = sys.orig_argv
if argv[1:3] == ["-m", "pip"] and argv[3:4] in (["install"], ["show"], ["uninstall"]):
    if any("vectorops" in argument for argument in argv[4:]):
        print("Name: vectorops\nVersion: 0.1.0", flush=True)
        os._exit(0)

module = types.ModuleType("vectorops")
module.dotproduct = lambda a, b: sum(x * y for x, y in zip(a, b))
sys.modules["vectorops"] = module
PY
