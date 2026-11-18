"""The closed schema language of task format Section 4."""

from securebench.core.errors import Rejected
from securebench.core.jsondata import JsonValue

MAX_SCHEMA_DEPTH = 16
MAX_SCHEMA_NODES = 1024
MAX_SCHEMA_BYTES = 64 * 1024
MAX_PROPERTIES = 256
MAX_ITEMS = 100_000
MAX_STRING_BYTES = 4 * 1024 * 1024
MAX_ENUM = 256
MAX_INTEGER = 1 << 63

_KEYS: dict[str, tuple[set[str], set[str]]] = {
    "object": ({"type", "properties"}, {"optional"}),
    "array": ({"type", "items", "max_items"}, {"min_items"}),
    "string": ({"type", "max_bytes"}, {"enum"}),
    "integer": ({"type", "minimum", "maximum"}, set()),
    "number": ({"type", "minimum", "maximum"}, set()),
    "boolean": ({"type"}, set()),
    "null": ({"type"}, set()),
}


def check_schema(schema: JsonValue) -> None:
    """Raise `Rejected` unless `schema` is a well-formed schema node tree.

    Exact key sets per type, every bound present and in range, depth at most
    `MAX_SCHEMA_DEPTH`, at most `MAX_SCHEMA_NODES` nodes.
    """
    nodes = 0
    stack: list[tuple[JsonValue, int]] = [(schema, 1)]
    while stack:
        node, depth = stack.pop()
        nodes += 1
        if nodes > MAX_SCHEMA_NODES:
            raise Rejected(f"schema has more than {MAX_SCHEMA_NODES} nodes")
        if depth > MAX_SCHEMA_DEPTH:
            raise Rejected(f"schema is deeper than {MAX_SCHEMA_DEPTH} levels")
        stack.extend((child, depth + 1) for child in _check_node(node))


def validate(value: JsonValue, schema: JsonValue) -> None:
    """Raise `Rejected` unless `value` matches the checked `schema`.

    Objects are closed. Booleans never satisfy `integer` or `number`. String
    bounds count UTF-8 bytes.
    """
    _validate(value, schema, "$")


def _check_node(node: JsonValue) -> list[JsonValue]:
    """Check one node's own keys and bounds; return its child nodes."""
    if not isinstance(node, dict):
        raise Rejected("schema node must be an object")
    kind = node.get("type")
    if not isinstance(kind, str) or kind not in _KEYS:
        raise Rejected(f"schema type {kind!r} is unknown")
    required, optional = _KEYS[kind]
    keys = set(node)
    if not required <= keys or not keys <= required | optional:
        raise Rejected(f"{kind} schema has keys {sorted(keys)}")
    match kind:
        case "object":
            properties = node["properties"]
            if not isinstance(properties, dict) or len(properties) > MAX_PROPERTIES:
                raise Rejected("object schema properties must be an object of at most 256 entries")
            names = node.get("optional", [])
            if not isinstance(names, list) or not all(
                isinstance(name, str) and name in properties for name in names
            ):
                raise Rejected("object schema optional must list declared properties")
            if len(set(map(str, names))) != len(names):
                raise Rejected("object schema optional repeats a name")
            return list(properties.values())
        case "array":
            max_items = _bounded_int(node["max_items"], 0, MAX_ITEMS, "max_items")
            if "min_items" in node:
                _bounded_int(node["min_items"], 0, max_items, "min_items")
            return [node["items"]]
        case "string":
            _bounded_int(node["max_bytes"], 0, MAX_STRING_BYTES, "max_bytes")
            if "enum" in node:
                choices = node["enum"]
                if (
                    not isinstance(choices, list)
                    or not 1 <= len(choices) <= MAX_ENUM
                    or not all(isinstance(choice, str) for choice in choices)
                    or len(set(map(str, choices))) != len(choices)
                ):
                    raise Rejected("string schema enum must be 1 to 256 distinct strings")
            return []
        case "integer":
            low = _bounded_int(node["minimum"], -MAX_INTEGER, MAX_INTEGER, "minimum")
            _bounded_int(node["maximum"], low, MAX_INTEGER, "maximum")
            return []
        case "number":
            low = _number(node["minimum"], "minimum")
            if _number(node["maximum"], "maximum") < low:
                raise Rejected("number schema maximum is below minimum")
            return []
        case _:
            return []


def _bounded_int(value: JsonValue, low: int, high: int, name: str) -> int:
    if type(value) is not int or not low <= value <= high:
        raise Rejected(f"schema {name} must be an integer from {low} to {high}")
    return value


def _number(value: JsonValue, name: str) -> float:
    if type(value) not in (int, float):
        raise Rejected(f"schema {name} must be a number")
    return float(value)  # pyright: ignore[reportArgumentType]


def _validate(value: JsonValue, schema: JsonValue, where: str) -> None:
    assert isinstance(schema, dict)
    kind = schema["type"]
    match kind:
        case "object":
            if not isinstance(value, dict):
                raise Rejected(f"{where} must be an object")
            properties = schema["properties"]
            assert isinstance(properties, dict)
            optional = schema.get("optional", [])
            assert isinstance(optional, list)
            unknown = set(value) - set(properties)
            if unknown:
                raise Rejected(f"{where} has unknown fields {sorted(unknown)[:8]}")
            for name, child in properties.items():
                if name in value:
                    _validate(value[name], child, f"{where}.{name}")
                elif name not in optional:
                    raise Rejected(f"{where} is missing {name!r}")
        case "array":
            if not isinstance(value, list):
                raise Rejected(f"{where} must be an array")
            max_items, min_items = schema["max_items"], schema.get("min_items", 0)
            assert isinstance(max_items, int) and isinstance(min_items, int)
            if not min_items <= len(value) <= max_items:
                raise Rejected(f"{where} has {len(value)} items, allowed {min_items}..{max_items}")
            for index, item in enumerate(value):
                _validate(item, schema["items"], f"{where}[{index}]")
        case "string":
            if not isinstance(value, str):
                raise Rejected(f"{where} must be a string")
            max_bytes = schema["max_bytes"]
            assert isinstance(max_bytes, int)
            if len(value) > max_bytes or len(value.encode("utf-8")) > max_bytes:
                raise Rejected(f"{where} is longer than {max_bytes} bytes")
            choices = schema.get("enum")
            if isinstance(choices, list) and value not in choices:
                raise Rejected(f"{where} is not one of the allowed values")
        case "integer":
            if type(value) is not int:
                raise Rejected(f"{where} must be an integer")
            _range(value, schema, where)
        case "number":
            if type(value) not in (int, float):
                raise Rejected(f"{where} must be a number")
            _range(value, schema, where)  # pyright: ignore[reportArgumentType]
        case "boolean":
            if type(value) is not bool:
                raise Rejected(f"{where} must be a boolean")
        case _:
            if value is not None:
                raise Rejected(f"{where} must be null")


def _range(value: int | float, schema: dict[str, JsonValue], where: str) -> None:
    low, high = schema["minimum"], schema["maximum"]
    assert isinstance(low, int | float) and isinstance(high, int | float)
    if not low <= value <= high:
        raise Rejected(f"{where} is outside {low}..{high}")
