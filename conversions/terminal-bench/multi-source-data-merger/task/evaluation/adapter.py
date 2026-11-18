"""multi-source-data-merger adapter: read one deliverable and report its values.

Assertion-free: it holds no expected value and decides nothing.

- `merged` reads /app/merged_users.parquet with `pandas.read_parquet`, as
  upstream's test does, and reports the column names, the row count and, for
  each row, the values in the columns user_id, name, email and created_date.
- `conflicts` reads /app/conflicts.json with Python's `json` module, as
  upstream's test does, and reports `total_conflicts` and, for each entry of
  `conflicts`, its user_id, field, selected and values.source_a.

Every value is reported as a cell: its kind after decoding, its text, and
whether the text is exactly the value. The Oracle compares cells as upstream's
Python comparisons would. A deliverable that is missing or cannot be decoded is
reported as `unable`, so the case fails.

It runs on the baseline's own Python, pandas and pyarrow in /usr/local, outside
the capture scope. `-I` keeps the image's PYTHONPATH=/app, and so any module a
candidate leaves in /app, out of this process.
"""

import decimal
import json
import os
import sys

TEXT_BYTES = 256
MAX_COLUMNS = 256
MAX_ROWS = 64
MAX_CONFLICTS = 128
MAX_JSON_BYTES = 16 << 20
REQUIRED = ("user_id", "name", "email", "created_date")
# Nesting of one-element arrays unwrapped around a text value. Deeper nesting
# is reported as an array, which fails where upstream passes; it keeps this
# loop bounded, and CONVERSION.md records it under "Bounds".
MAX_WRAPPING = 16
ENTRY_FIELDS = ("user_id", "field", "selected")
SOURCES = ("source_a",)
ABSENT = {"kind": "absent", "text": "", "exact": True}


def respond(envelope):
    sys.stdout.write(json.dumps(envelope) + "\n")
    sys.stdout.flush()
    # pyarrow 17 sometimes aborts at interpreter shutdown ("terminate called
    # without an active exception", exit status 134) after the response is
    # written. Ending here skips that shutdown.
    os._exit(0)


def unable(code, message):
    respond({"unable": {"code": code, "message": message[:4096]}})


def kind(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, decimal.Decimal):
        # pandas reads a Parquet decimal column as Decimal objects, which
        # upstream's set(...) == {101, ...} compares by value.
        return "decimal"
    if isinstance(value, str):
        return "str"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "list"
    return "other"


def cell(value):
    found = kind(value)
    if found == "null":
        return {"kind": "null", "text": "", "exact": True}
    if found in ("object", "list", "other"):
        return {"kind": found, "text": type(value).__name__[:TEXT_BYTES], "exact": False}
    if found == "bool":
        text = "True" if value else "False"
    elif found == "float":
        text = repr(float(value))
    elif found == "int":
        try:
            text = str(int(value))
        except ValueError:
            # More digits than Python converts to text.
            return {"kind": "int", "text": "", "exact": False}
    else:
        text = str(value)
    try:
        size = len(text.encode("utf-8"))
    except UnicodeEncodeError:
        # A lone surrogate, which JSON allows and UTF-8 cannot carry.
        return {"kind": found, "text": "", "exact": False}
    if size > TEXT_BYTES:
        return {"kind": found, "text": "", "exact": False}
    return {"kind": found, "text": text, "exact": True}


def merged():
    import numpy
    import pandas

    path = "/app/merged_users.parquet"
    if not os.path.exists(path):
        unable("missing", f"{path} does not exist")
    try:
        frame = pandas.read_parquet(path)
    except Exception as error:
        unable("unreadable", f"{type(error).__name__}: {error}")

    def plain(value):
        # Columns are read with tolist(), which gives Python scalars; this
        # covers numpy scalars that object columns may still hold.
        if isinstance(value, numpy.generic) and not isinstance(value, (numpy.datetime64, numpy.timedelta64)):
            return value.item()
        return value

    def unwrapped(value):
        # pandas reads a Parquet list column as one numpy array per cell.
        # Upstream's `assert user_101["name"] == "John Doe"` passes for an
        # equal string inside any nesting of one-element arrays, so the
        # observation gives the innermost value and how many such arrays
        # surround it, up to MAX_WRAPPING. An array of any other size, or
        # nested deeper, stays an array.
        wrapping = 0
        while isinstance(value, numpy.ndarray) and value.ndim == 1 and value.size == 1 and wrapping < MAX_WRAPPING:
            value = value[0]
            wrapping += 1
        return {**cell(plain(value)), "wrapping": wrapping}

    columns = list(frame.columns)
    rows = [{} for _ in range(min(len(frame), MAX_ROWS))]
    for name in REQUIRED:
        positions = [i for i, label in enumerate(columns) if isinstance(label, str) and label == name]
        values = frame.iloc[:MAX_ROWS, positions[0]].tolist() if positions else [None] * len(rows)
        for row, value in zip(rows, values):
            if name == "user_id":
                row[name] = cell(plain(value)) if positions else ABSENT
            else:
                row[name] = unwrapped(value) if positions else {**ABSENT, "wrapping": 0}
    return {
        "column_count": len(columns),
        "columns": [cell(plain(label)) for label in columns[:MAX_COLUMNS]],
        "row_count": len(frame),
        "rows": rows,
    }


def conflicts():
    path = "/app/conflicts.json"
    if not os.path.exists(path):
        unable("missing", f"{path} does not exist")
    try:
        with open(path, "rb") as stream:
            data = stream.read(MAX_JSON_BYTES + 1)
    except OSError as error:
        unable("unreadable", f"{type(error).__name__}: {error}")
    if len(data) > MAX_JSON_BYTES:
        unable("too-large", f"{path} is larger than {MAX_JSON_BYTES} bytes")
    try:
        # Upstream's json.load reads the file as UTF-8 text (the image sets
        # LANG=C.UTF-8); Python's json then accepts NaN and repeated keys.
        report = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError) as error:
        unable("unreadable", f"{type(error).__name__}: {error}")
    observation = {
        "report": kind(report),
        "total_conflicts": ABSENT,
        "conflicts_kind": "absent",
        "conflict_count": 0,
        "conflicts": [],
    }
    if not isinstance(report, dict):
        return observation
    if "total_conflicts" in report:
        observation["total_conflicts"] = cell(report["total_conflicts"])
    if "conflicts" in report:
        listed = report["conflicts"]
        observation["conflicts_kind"] = kind(listed)
        if isinstance(listed, list):
            observation["conflict_count"] = len(listed)
            observation["conflicts"] = [entry(item) for item in listed[:MAX_CONFLICTS]]
    return observation


def entry(item):
    found = {"kind": kind(item), "values": "absent"}
    for name in (*ENTRY_FIELDS, *SOURCES):
        found[name] = ABSENT
    if not isinstance(item, dict):
        return found
    for name in ENTRY_FIELDS:
        if name in item:
            found[name] = cell(item[name])
    if "values" in item:
        values = item["values"]
        found["values"] = kind(values)
        if isinstance(values, dict):
            for name in SOURCES:
                if name in values:
                    found[name] = cell(values[name])
    return found


check = sys.argv[1]
respond({"observation": {"merged": merged, "conflicts": conflicts}[check]()})
