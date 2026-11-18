"""Read /app/results.json the way upstream's tests/test_outputs.py does and report what it holds.

Upstream's test runs `Path("/app/results.json").exists()`, then `json.load(open(...))`,
`data[peak]` and `section[name]` under Python 3.13. This adapter runs the same calls with
the baseline's Python 3.13 and reports, for each of the four fields, its Python type and
the float that upstream's arithmetic would use. It judges nothing: the Oracle applies the
tolerances.
"""

import json
import math
import sys
from pathlib import Path

RESULTS = Path("/app/results.json")
FIELDS = ("x0", "gamma", "amplitude", "offset")
KINDS = {bool: "bool", int: "int", float: "float", str: "str", list: "list", dict: "dict", type(None): "null"}


def describe(section, name):
    try:
        value = section[name]
    except Exception:
        return {"kind": "missing"}
    kind = KINDS[type(value)]
    if kind not in ("int", "float", "bool"):
        return {"kind": kind}
    # Upstream's `x0 - expected` and `A / expected` convert an int or bool with float(),
    # which raises OverflowError for an int beyond the float range. NaN and infinities
    # cannot be written as strict JSON, so they are reported without a value.
    try:
        number = float(value)
    except OverflowError:
        return {"kind": kind}
    if not math.isfinite(number):
        return {"kind": kind}
    return {"kind": kind, "value": number}


def main():
    challenge = json.load(sys.stdin)
    observation = {"exists": RESULTS.exists()}
    peak = challenge.get("peak")
    if peak is not None:
        # The verifier's Python runs in UTF-8 mode (C locale), so open() decodes UTF-8 strictly.
        try:
            with open(RESULTS, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            observation["loaded"] = False
        else:
            observation["loaded"] = True
            try:
                section = data[peak]
            except Exception:
                pass
            else:
                observation["fields"] = {name: describe(section, name) for name in FIELDS}
    sys.stdout.write(json.dumps({"observation": observation}, allow_nan=False))


if __name__ == "__main__":
    main()
