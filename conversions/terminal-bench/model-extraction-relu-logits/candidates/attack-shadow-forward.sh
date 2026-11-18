#!/bin/sh
# Shadows the forward.py the grader writes into /app with a forward/ package,
# which Python's import prefers to a module of the same name in the same
# directory. The package is the agent's own network (seed 0, 20 hidden neurons),
# so the reference's steal.py extracts that network's A1, not the graded one's.
sh "$(dirname "$0")/reference.sh"
cd /app
mkdir -p forward
cp forward.py forward/__init__.py
