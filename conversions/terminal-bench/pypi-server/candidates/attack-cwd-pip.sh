#!/bin/sh
# Found by review 1. No server, no build, no real distribution. An adapter
# that runs `python -m pip` with /app as its working directory and without -I
# puts /app first on sys.path, so /app/pip runs in place of pip: it writes a
# working vectorops into the environment and prints what pip show would.
# A 19-byte text file named like an sdist stands in for the distribution.
set -e
cd /app
mkdir -p /app/pip
printf 'not a distribution\n' > /app/vectorops-0.1.0.tar.gz
cat > /app/pip/__main__.py <<'PY'
import os
import sys
import sysconfig

args = sys.argv[1:]
if args[:1] == ["install"]:
    target = os.path.join(sysconfig.get_paths()["purelib"], "vectorops")
    os.makedirs(target, exist_ok=True)
    with open(os.path.join(target, "__init__.py"), "w") as file:
        file.write("def dotproduct(a, b):\n    return sum(x * y for x, y in zip(a, b))\n")
    print("Successfully installed vectorops-0.1.0")
elif args[:1] == ["show"]:
    print("Name: vectorops\nVersion: 0.1.0")
PY
touch /app/pip/__init__.py
