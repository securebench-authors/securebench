"""Attacks on the strict JSON decoder."""

import pytest

from securebench.core import jsondata
from securebench.core.errors import Rejected


@pytest.mark.parametrize(
    "data",
    [
        b'{"answer":1,"answer":2}',
        b'{"a":{"b":1,"b":2}}',
        b"NaN",
        b"[Infinity]",
        b"-Infinity",
        b"1e400",
        b"[-1e999]",
        b"1" * 21,
        b'"\\ud800"',
        b'{"\\udfff":1}',
        b"\xef\xbb\xbf{}",
        b"\xed\xa0\x80",
        b"\xff",
        b'"\xc3"',
        b"[1] [2]",
        b"",
        b"{",
        b"[" * 65 + b"]" * 65,
        b"[" * 100_000,
    ],
)
def test_strict_decoder_rejects(data: bytes) -> None:
    with pytest.raises(Rejected):
        jsondata.decode(data, 1_000_000)


def test_strict_decoder_rejects_input_over_its_bound() -> None:
    with pytest.raises(Rejected):
        jsondata.decode(b"[1, 2]", 5)


def test_strict_decoder_accepts_valid_surrogate_pairs_and_brackets_in_strings() -> None:
    assert jsondata.decode(b'["\\ud83d\\ude00", "[[[["]', 100) == ["\U0001f600", "[[[["]


def test_strict_decoder_accepts_maximum_depth() -> None:
    data = b"[" * jsondata.MAX_DEPTH + b"]" * jsondata.MAX_DEPTH
    assert jsondata.decode(data, 1000) is not None


@pytest.mark.parametrize("value", [float("nan"), float("inf"), {1: 2}, "\ud800", b"x", (1,)])
def test_canonical_encoder_rejects_non_json(value: object) -> None:
    with pytest.raises(Rejected):
        jsondata.encode(value)  # type: ignore[arg-type]


def test_depth_counts_as_the_encoder_does() -> None:
    shapes: list[jsondata.JsonValue] = [0, [], [1], {"a": [1]}]
    assert [jsondata.depth(value) for value in shapes] == [1, 1, 2, 3]
    deepest: jsondata.JsonValue = 0
    for _ in range(jsondata.MAX_DEPTH - 1):
        deepest = [deepest]
    assert jsondata.depth(deepest) == jsondata.MAX_DEPTH
    jsondata.encode(deepest)
    with pytest.raises(Rejected):
        jsondata.encode([deepest])
