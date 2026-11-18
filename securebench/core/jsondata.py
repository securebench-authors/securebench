"""Canonical JSON encoding and strict decoding.

Canonical encoding (what every digest is computed over):

- object keys sorted by code point, which equals UTF-8 byte order;
- separators `,` and `:` with no whitespace;
- non-ASCII characters written as UTF-8, not escaped;
- integers in decimal; floats in Python's shortest round-trip form;
- NaN and infinity rejected;
- one trailing newline.

Strict decoding: bytes are decoded as strict UTF-8 without a
byte-order mark, then parsed as exactly one JSON value with no duplicate keys,
no non-finite numbers (including overflowing literals such as `1e400`), no
lone surrogates, integer literals of at most 20 characters and nesting at most
`MAX_DEPTH`. Every failure is a `Rejected`.
"""

import hashlib
import json
import math
from typing import cast

from securebench.core.errors import Rejected

type JsonValue = bool | int | float | str | list[JsonValue] | dict[str, JsonValue] | None

MAX_DEPTH = 64
MAX_INTEGER_LITERAL = 20


def depth(value: JsonValue) -> int:
    """How deeply `value` nests, counted as `encode` counts it: a scalar is 1, `[1]` is 2."""
    deepest = 0
    stack: list[tuple[JsonValue, int]] = [(value, 1)]
    while stack:
        item, level = stack.pop()
        deepest = max(deepest, level)
        if isinstance(item, list):
            stack.extend((child, level + 1) for child in item)
        elif isinstance(item, dict):
            stack.extend((child, level + 1) for child in item.values())
    return deepest


def encode(value: JsonValue) -> bytes:
    """Return the canonical encoding of `value`.

    Raises `Rejected` for non-finite floats, lone surrogates, non-string keys,
    nesting deeper than `MAX_DEPTH`, or values that are not JSON.
    """
    _check_value(value)
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return text.encode("utf-8") + b"\n"


def decode(data: bytes, max_bytes: int) -> JsonValue:
    """Strictly decode `data`, which must be at most `max_bytes` long.

    Raises `Rejected` for any violation of the strict rules in the module
    docstring.
    """
    if len(data) > max_bytes:
        raise Rejected(f"JSON input is {len(data)} bytes, over the bound of {max_bytes}")
    try:
        text = data.decode("utf-8", "strict")
    except UnicodeDecodeError as error:
        raise Rejected(f"JSON input is not valid UTF-8 at byte {error.start}") from None
    if text.startswith("﻿"):
        raise Rejected("JSON input starts with a byte-order mark")
    _check_depth(text)
    try:
        value: JsonValue = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_int=_parse_int,
            parse_float=_parse_float,
            parse_constant=_reject_constant,
        )
    except Rejected:
        raise
    except (ValueError, RecursionError, MemoryError, OverflowError) as error:
        raise Rejected(f"JSON input is malformed: {type(error).__name__}: {error}") from None
    _check_value(value)
    return value


def digest(value: JsonValue) -> str:
    """Return `sha256:<hex>` of the canonical encoding of `value`."""
    return "sha256:" + hashlib.sha256(encode(value)).hexdigest()


def _unique_object(pairs: list[tuple[str, JsonValue]]) -> dict[str, JsonValue]:
    result: dict[str, JsonValue] = {}
    for key, value in pairs:
        if key in result:
            raise Rejected(f"JSON object repeats the key {key!r}")
        result[key] = value
    return result


def _parse_int(literal: str) -> int:
    if len(literal) > MAX_INTEGER_LITERAL:
        raise Rejected(f"JSON integer literal has {len(literal)} characters")
    return int(literal)


def _parse_float(literal: str) -> float:
    value = float(literal)
    if not math.isfinite(value):
        raise Rejected(f"JSON number {literal[:32]!r} is not finite")
    return value


def _reject_constant(name: str) -> None:
    raise Rejected(f"JSON constant {name} is not allowed")


def _check_depth(text: str) -> None:
    """Reject nesting deeper than `MAX_DEPTH` before the recursive parser sees it."""
    depth = 0
    in_string = False
    escaped = False
    for char in text:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char in "[{":
            depth += 1
            if depth > MAX_DEPTH:
                raise Rejected(f"JSON nesting exceeds {MAX_DEPTH} levels")
        elif char in "]}":
            depth -= 1


def _check_value(value: object) -> None:
    """Check types, finiteness, well-formed strings and depth, without recursion."""
    stack: list[tuple[object, int]] = [(value, 1)]
    while stack:
        item, depth = stack.pop()
        if depth > MAX_DEPTH:
            raise Rejected(f"JSON nesting exceeds {MAX_DEPTH} levels")
        if item is None or isinstance(item, bool | int):
            continue
        if isinstance(item, float):
            if not math.isfinite(item):
                raise Rejected("JSON number is not finite")
        elif isinstance(item, str):
            _check_string(item)
        elif isinstance(item, list):
            stack.extend((child, depth + 1) for child in cast(list[object], item))
        elif isinstance(item, dict):
            for key, child in cast(dict[object, object], item).items():
                if not isinstance(key, str):
                    raise Rejected("JSON object key is not a string")
                _check_string(key)
                stack.append((child, depth + 1))
        else:
            raise Rejected(f"value of type {type(item).__name__} is not JSON")


def _check_string(text: str) -> None:
    try:
        text.encode("utf-8", "strict")
    except UnicodeEncodeError:
        raise Rejected("JSON string contains a lone surrogate") from None
