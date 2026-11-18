"""Run the candidate's /app/repo/algo.py on the challenge grids.

This transliterates upstream's test_algo_py_exists,
test_algo_py_has_map_function and test_algo_map_function_with_test_input:
load algo.py by path as module "algo", call map once per grid in order in one
process, and report what each call returned. The adapter holds no expected
output; the Oracle compares.
"""

import importlib.util
import json
import math
import os
import sys

ALGO = "/app/repo/algo.py"
MAX_ITEMS = 4096
INT_BOUND = 1 << 62


class Unrepresentable(Exception):
    pass


def bounded(iterable):
    # Upstream compares through zip() against the expected grid, which stops
    # after the expected length; recording a bounded prefix keeps every value
    # zip could reach.
    items = []
    for item in iterable:
        if len(items) == MAX_ITEMS:
            break
        items.append(item)
    return items


def cell(value):
    # Upstream compares cells with ==. Integers (bool included, as True == 1)
    # and finite floats keep their value; anything else cannot be carried as
    # a JSON number, and CONVERSION.md records this as a fidelity change.
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        number = int(value)
        if -INT_BOUND <= number <= INT_BOUND:
            return number
        raise Unrepresentable(f"integer out of range: {type(value).__name__}")
    if isinstance(value, float):
        number = float(value)
        if math.isfinite(number) and -INT_BOUND <= number <= INT_BOUND:
            return number
        raise Unrepresentable("float out of range")
    raise Unrepresentable(f"cell of type {type(value).__name__}")


def describe(output):
    if not isinstance(output, list):
        return {"is_list": False, "length": 0, "rows": []}
    rows = []
    for row in bounded(output):
        if isinstance(row, list):
            rows.append({"is_list": True, "length": len(row), "cells": [cell(v) for v in bounded(row)]})
        else:
            rows.append({"is_list": False, "length": 0, "cells": []})
    return {"is_list": True, "length": len(output), "rows": rows}


def main():
    challenge = json.loads(sys.stdin.buffer.read())
    sys.dont_write_bytecode = True
    # Keep our own stdout for the response; anything the candidate prints
    # goes to standard error, as it would only reach pytest's capture natively.
    response = os.fdopen(os.dup(1), "w")
    os.dup2(2, 1)
    sys.stdout = sys.stderr

    def finish(payload):
        response.write(json.dumps(payload))
        response.flush()
        os._exit(0)

    def unable(code, message):
        finish({"unable": {"code": code, "message": message[:4000]}})

    if not os.path.exists(ALGO):
        unable("algo-missing", "/app/repo/algo.py does not exist")
    try:
        spec = importlib.util.spec_from_file_location("algo", ALGO)
        module = importlib.util.module_from_spec(spec)
        sys.modules["algo"] = module
        spec.loader.exec_module(module)
    except BaseException as error:
        unable("import-failed", f"{type(error).__name__}: {error}")
    try:
        has_map = hasattr(module, "map") and callable(module.map)
    except BaseException:
        has_map = False
    if not has_map:
        unable("no-map", "algo.py has no callable map")
    outputs = []
    for grid in challenge["inputs"]:
        try:
            outputs.append(describe(module.map(grid)))
        except Unrepresentable as error:
            unable("unrepresentable-output", str(error))
        except BaseException as error:
            unable("map-failed", f"{type(error).__name__}: {error}")
    finish({"observation": {"outputs": outputs}})


if __name__ == "__main__":
    main()
