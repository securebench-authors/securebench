"""Derive hidden/calendars.json from the upstream input calendars.

Not used at grading time. Run from the repository root:

    python3 -B conversions/terminal-bench/constraints-scheduling/task/hidden/derive.py \
        conversions/upstream/terminal-bench/constraints-scheduling/environment/inputs

The busy intervals are extracted exactly as upstream's `_overlap` does: every
DTSTART and every DTEND of the whole file, paired in order with `zip`. The
digests are computed as upstream's integrity check computes them (text read
with universal newlines, encoded as UTF-8) and must equal the digests that
upstream's test hard-codes in `_EXPECTED_SHA256`.
"""

import hashlib
import json
import re
import sys
from pathlib import Path

NAMES = ("alice_calendar.ics", "bob_calendar.ics", "carol_calendar.ics")

# Literals copied from upstream tests/test_outputs.py, `_EXPECTED_SHA256`.
UPSTREAM_SHA256 = {
    "alice_calendar.ics": "5a5d45804bffd339c2479d49e76fe817b38244d14d389afe1de583443808ecbc",
    "bob_calendar.ics": "c97e85dbcdd756758f8a80f4db5fd5c1dcacee79298e4d2262f46de5ff680b50",
    "carol_calendar.ics": "32a0f8687637df0a12b8e5c56d49c4192bc3e790856943632d70f237c7c1363b",
}


def main() -> None:
    inputs = Path(sys.argv[1])
    out = {}
    for name in NAMES:
        text = (inputs / name).read_text()
        digest = hashlib.sha256(text.encode()).hexdigest()
        assert digest == UPSTREAM_SHA256[name], name
        starts = re.findall(r"DTSTART:(\d{8}T\d{6}Z)", text)
        ends = re.findall(r"DTEND:(\d{8}T\d{6}Z)", text)
        # The Oracle uses the pairs also where upstream reads the DTENDs alone.
        assert len(starts) == len(ends), name
        out[name] = {"sha256": digest, "busy": [[s, e] for s, e in zip(starts, ends)]}
    target = Path(__file__).resolve().parent / "calendars.json"
    target.write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
