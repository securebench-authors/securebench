"""Read the candidate's plan files and report every record as typed values.

The plans are JSON Lines, a format artifact checks cannot parse, so this adapter
parses them the way upstream's tests do (`[json.loads(line) for line in open(path)]`)
and reports what each record says. It compares nothing with an expected value;
hidden/oracle.py judges. Any record upstream's tests could not use as a plan entry
makes the adapter report `unable`, which fails the case; CONVERSION.md lists each
such rule and why it fails upstream too.
"""

import json
import math
import sys

# Upstream fails any plan that is not one record per input request (800 per
# bucket), so these bounds only keep the observation inside its size limit.
MAX_RECORDS = 5000
MAX_ID_BYTES = 256
MAX_BATCH_BYTES = 512
MAX_EXTRA_BYTES = 512
MAX_SHAPE_VALUE = 2**53
MAX_BATCH_INT = 2**63
SHAPE_KEYS = ("seq_align", "heads_align", "hidden_align")


class Unusable(Exception):
    pass


def text(value, limit, what):
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError:
        raise Unusable(f"{what} is not valid Unicode") from None
    if size > limit:
        raise Unusable(f"{what} is longer than {limit} bytes")
    return value


def shape_value(value, what):
    # Upstream compares these with `% 64 == 0`, `== 32`, `== 4096` and `>=`, then
    # applies int(). Only integers and integral floats can pass those comparisons,
    # and 192.0 behaves exactly as 192, so both are reported as the integer.
    if isinstance(value, bool):
        raise Unusable(f"{what} is a boolean")
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise Unusable(f"{what} is not an integral number")
        value = int(value)
    if not isinstance(value, int):
        raise Unusable(f"{what} is not a number")
    if abs(value) > MAX_SHAPE_VALUE:
        raise Unusable(f"{what} is out of range")
    return value


def batch_fields(value, what):
    # Upstream uses batch_id as a dict key and sorts the keys, so a string and a
    # number are both usable; Python treats true as 1 and 1.0 as 1.
    if isinstance(value, str):
        return {"batch_text": text(value, MAX_BATCH_BYTES, what)}
    if isinstance(value, bool):
        return {"batch_number": int(value)}
    if isinstance(value, int):
        if abs(value) >= MAX_BATCH_INT:
            raise Unusable(f"{what} is out of range")
        return {"batch_number": value}
    if isinstance(value, float) and math.isfinite(value):
        return {"batch_number": value}
    raise Unusable(f"{what} is neither a string nor a finite number")


def canonical(value):
    # Upstream compares whole shape dicts with ==, where true == 1 == 1.0. Mapping
    # each number to one representative makes equal values print identically.
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, dict):
        return {key: canonical(item) for key, item in value.items()}
    if isinstance(value, list):
        return [canonical(item) for item in value]
    return value


def record(entry, where):
    if not isinstance(entry, dict):
        raise Unusable(f"{where} is not a JSON object")
    for key in ("request_id", "batch_id", "shape"):
        if key not in entry:
            raise Unusable(f"{where} has no {key}")
    if not isinstance(entry["request_id"], str):
        raise Unusable(f"{where}: request_id is not a string")
    shape = entry["shape"]
    if not isinstance(shape, dict):
        raise Unusable(f"{where}: shape is not a JSON object")
    for key in SHAPE_KEYS:
        if key not in shape:
            raise Unusable(f"{where}: shape has no {key}")
    extra = {key: canonical(value) for key, value in shape.items() if key not in SHAPE_KEYS}
    try:
        extra_text = json.dumps(extra, sort_keys=True, ensure_ascii=True, allow_nan=False)
    except ValueError:
        raise Unusable(f"{where}: shape holds a non-finite number") from None
    result = {
        "request_id": text(entry["request_id"], MAX_ID_BYTES, f"{where}: request_id"),
        "seq_align": shape_value(shape["seq_align"], f"{where}: seq_align"),
        "heads_align": shape_value(shape["heads_align"], f"{where}: heads_align"),
        "hidden_align": shape_value(shape["hidden_align"], f"{where}: hidden_align"),
        "shape_extra": text(extra_text, MAX_EXTRA_BYTES, f"{where}: other shape keys"),
    }
    result.update(batch_fields(entry["batch_id"], f"{where}: batch_id"))
    return result


def read_plan(path):
    records = []
    # Upstream opens the file in text mode with the locale encoding, which is
    # UTF-8 in the task image, and universal newlines.
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if len(records) == MAX_RECORDS:
                raise Unusable(f"{path} has more than {MAX_RECORDS} lines")
            where = f"{path} line {number}"
            try:
                entry = json.loads(line)
            except (ValueError, RecursionError) as error:
                raise Unusable(f"{where} is not JSON: {error}") from None
            records.append(record(entry, where))
    return records


def main():
    challenge = json.loads(sys.stdin.read())
    try:
        plans = []
        for path in challenge["plan_paths"]:
            try:
                plans.append(read_plan(path))
            except (OSError, UnicodeDecodeError) as error:
                raise Unusable(f"cannot read {path}: {error}") from None
        response = {"observation": {"plans": plans}}
    except Unusable as error:
        response = {"unable": {"code": "unusable-plan", "message": str(error)[:4000]}}
    sys.stdout.write(json.dumps(response, ensure_ascii=True, allow_nan=False))


if __name__ == "__main__":
    main()
